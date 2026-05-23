import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Slot, Signal, QFile
from PySide6.QtUiTools import QUiLoader
from peripherals.VCU import VCU
from functools import partial
import pyqtgraph as pg
import time, math
from collections import deque

class DraggablePoint(pg.TargetItem):
    def __init__(self, x, y, index, callback):
        super().__init__(
            pos=(x, y),
            movable=True,
            size=12,
            symbol='o'
        )
        self.index = index
        self.fixed_x = x
        self.callback = callback

        # Called continuously while dragging
        self.sigPositionChanged.connect(self.on_move)

    def on_move(self):
        pos = self.pos()

        # Lock X axis
        self.setPos(self.fixed_x, pos.y())
        if(self.index == 0):
            self.setPos(self.fixed_x, 0)
        if(self.index == 17):
            self.setPos(self.fixed_x, 100)
        if(pos.y() > 100):
            self.setPos(self.fixed_x, 100)
        elif(pos.y() < 0):
            self.setPos(self.fixed_x, 0)
        # Notify parent
        self.callback(self.index, pos.y())


class VCUWidget(QtWidgets.QMainWindow):
    def __init__(self, peripheral):
        super().__init__()
        #add ui file loading here
        self.vcu = peripheral
        
        loader = QUiLoader()
        ui_file = QFile("ui\\VCU.ui")
        ui_file.open(QFile.ReadOnly)
        loader.registerCustomWidget(pg.PlotWidget)
        self.window = loader.load(ui_file,None)
        ui_file.close()
        
        self.setupGraph()
        self.window.setPedalMapButton.clicked.connect(self.sendPedalMap)

        # BPS/APPS threshold buttons
        self.window.sendAPPSSignal.clicked.connect(self.sendAPPS1SignalThresholds)
        self.window.sendAPPSSignal_2.clicked.connect(self.sendAPPS2SignalThresholds)
        self.window.sendBPSFault.clicked.connect(self.sendBPSFFaultThresholds)
        self.window.sendBPSFault_2.clicked.connect(self.sendBPSRFaultThresholds)
        self.window.sendAPPSFault.clicked.connect(self.sendAPPS1FaultThresholds)
        self.window.sendAPPSFault_2.clicked.connect(self.sendAPPS2FaultThresholds)
        self.window.sendBPSEngaged.clicked.connect(self.sendBPSEngagedThresholds)
        self.window.sendMaxTorque.clicked.connect(self.sendMaxTorque)

    
    def setupGraph(self):
        self.window.pedalGraph.getViewBox().disableAutoRange()
        self.start_time = time.perf_counter()
        self.sources = ["pedalMap"]
        self.buffers = {
            "pedalMap": [0, 0, 0, 0, 0, 0, 0, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 100],
            "x": [x * 6.25 for x in range(18)]
        }
        self.window.pedalGraph.setXRange(0, 100)
        self.window.pedalGraph.setYRange(0, 100)
        self.window.pedalGraph.showGrid(x=True, y=True)
        self.window.pedalGraph.setLabel('bottom', 'Pedal Input %')
        self.window.pedalGraph.setLabel('left', 'Output %')
        self.window.pedalGraph.setMouseEnabled(x=False, y=False)
        # Main mapping curve
        self.curves = {
            "pedalMap": self.window.pedalGraph.plot(
                self.buffers["x"],
                self.buffers["pedalMap"],
                pen=pg.mkPen('r', width=1.5)
            )
        }

        # Draggable control points
        self.points = []
        for i, (x, y) in enumerate(zip(self.buffers["x"], self.buffers["pedalMap"])):
            point = DraggablePoint(
                x=x,
                y=y,
                index = i,
                callback=self.updateGraph
            )
            self.window.pedalGraph.addItem(point)
            self.points.append(point)

        # Collect spin box references in index order (pointInput1 = index 0, etc.)
        self.spinboxes = [
            getattr(self.window, f"pointInput{n}") for n in range(1, 19)
        ]

        # Configure and connect spin boxes for editable points (skip index 0 and 17)
        for i, sb in enumerate(self.spinboxes):
            sb.setRange(0.0, 100.0)
            sb.setDecimals(2)
            sb.setSingleStep(0.5)
            sb.setValue(self.buffers["pedalMap"][i])
            if i == 0 or i == 17:
                sb.setReadOnly(True)
            else:
                # Use a default-argument capture to bind the correct index
                sb.valueChanged.connect(lambda val, idx=i: self.onSpinBoxChanged(idx, val))

    def onSpinBoxChanged(self, index, value):
        """Called when the user edits a spin box — updates the graph point and buffer."""
        # Update internal buffer and VCU state
        self.buffers["pedalMap"][index] = value
        self.vcu.state["pedalMap"] = self.buffers["pedalMap"]
        # Move the draggable point (block its position-change signal to avoid loops)
        self.points[index].sigPositionChanged.disconnect()
        self.points[index].setPos(self.buffers["x"][index], value)
        self.points[index].sigPositionChanged.connect(self.points[index].on_move)
        # Redraw curve
        self.curves["pedalMap"].setData(
            self.buffers["x"],
            self.buffers["pedalMap"]
        )

    def updateGraph(self, index, value):
        if(index == 0):
            self.setPos(self.fixed_x, 0)
        if(index == 17):
            self.setPos(self.fixed_x, 100)
        if(value > 100):
            self.setPos(self.fixed_x, 100)
        elif(value < 0):
            self.setPos(self.fixed_x, 0)
        # Update internal mapping
        self.buffers["pedalMap"][index] = value
        self.vcu.state["pedalMap"] = self.buffers["pedalMap"]
        # Sync the corresponding spin box without triggering valueChanged
        if index != 0 and index != 17:
            sb = self.spinboxes[index]
            sb.blockSignals(True)
            sb.setValue(value)
            sb.blockSignals(False)
        # Update curve
        self.curves["pedalMap"].setData(
            self.buffers["x"],
            self.buffers["pedalMap"]
        )

        # Debug print


    def sendPedalMap(self):
        """Send all 16 editable pedal map points to the VCU over CAN.

        Param IDs 0x0100–0x010F correspond to pedal map points 1–16,
        which are buffer indices 1–16 (endpoints 0 and 17 are fixed in
        the VCU and have no param ID).
        """
        PEDAL_MAP_BASE_ID = 0x0100
        for i in range(1, 17):                          # indices 1–16 inclusive
            param_id = PEDAL_MAP_BASE_ID + (i - 1)     # 0x0100, 0x0101, … 0x010F
            self.vcu.set_param(param_id, float(self.buffers["pedalMap"][i]))

    def sendAPPS1SignalThresholds(self):
        self.vcu.set_param(0x0004, float(self.window.appsHSignal.value()))   # APP1 Signal High
        self.vcu.set_param(0x0003, float(self.window.appsLSignal.value()))   # APP1 Signal Low

    def sendAPPS2SignalThresholds(self):
        self.vcu.set_param(0x0008, float(self.window.appsHSignal_2.value())) # APP2 Signal High
        self.vcu.set_param(0x0007, float(self.window.appsLSignal_2.value())) # APP2 Signal Low

    def sendBPSFFaultThresholds(self):
        self.vcu.set_param(0x000A, float(self.window.bpsHFault.value()))     # BSEF Fault High
        self.vcu.set_param(0x0009, float(self.window.bpsLFault.value()))     # BSEF Fault Low

    def sendBPSRFaultThresholds(self):
        self.vcu.set_param(0x000C, float(self.window.bpsHFault_2.value()))   # BSER Fault High
        self.vcu.set_param(0x000B, float(self.window.bpsLFault_2.value()))   # BSER Fault Low

    def sendAPPS1FaultThresholds(self):
        self.vcu.set_param(0x0002, float(self.window.appsHFault.value()))    # APP1 Fault High
        self.vcu.set_param(0x0001, float(self.window.appsLFault.value()))    # APP1 Fault Low

    def sendAPPS2FaultThresholds(self):
        self.vcu.set_param(0x0006, float(self.window.appsHFault_2.value()))  # APP2 Fault High
        self.vcu.set_param(0x0005, float(self.window.appsLFault_2.value()))  # APP2 Fault Low

    def sendMaxTorque(self):
        self.vcu.set_param(0x000F, float(self.window.maxTorque.value()))     # Maximum Torque Request

    def sendBPSEngagedThresholds(self):
        self.vcu.set_param(0x000D, float(self.window.bpsfEngaged.value()))   # BSEF Engaged
        self.vcu.set_param(0x000E, float(self.window.bpsrEngaged.value()))   # BSER Engaged

    @Slot()  
    def show(self):
        self.window.raise_()
        self.window.show()