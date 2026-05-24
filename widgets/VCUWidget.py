import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QTimer, Slot, Signal, QFile
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
    window_closed = Signal()
    logger = Signal(str)
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
        self.window.sendConfigButton.clicked.connect(self.vcu.writeConfiguration)
        # BPS/APPS threshold buttons
        for btn_name, (param_id, widget_name, info) in self.vcu.const.button_map.items():
            widget = getattr(self.window, widget_name)
            getattr(self.window, btn_name).clicked.connect(
                lambda checked=False, pid=param_id, w=widget, info=info: self.vcu.set_param(pid, float(w.value()),info))
            

        
        
        self.window_closed.connect(partial(self.vcu.disable))

    def closeEvent(self, event):
        self.window_closed.emit()
        event.accept()

    def setupGraph(self):
        self.window.pedalGraph.getViewBox().disableAutoRange()
        self.start_time = time.perf_counter()
        self.sources = ["pedalMap"]
        self.buffers = {
            "pedalMap": [0, 0, 0, 0, 0, 0, 0, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 1],
            "x": [x * 6.25 for x in range(18)]
        }
        self.window.pedalGraph.setXRange(0, 100)
        self.window.pedalGraph.setYRange(0, 1)
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
            sb.setRange(0.0, 1.0)
            sb.setDecimals(2)
            sb.setSingleStep(0.5)
            sb.setValue(self.buffers["pedalMap"][i])
            if i == 0 or i == 17:
                sb.setReadOnly(True)
            else:
                # Use a default-argument capture to bind the correct index
                sb.valueChanged.connect(lambda val, idx=i: self.onSpinBoxChanged(idx, val))

    def onSpinBoxChanged(self, index, value):
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
            value = 0
        if(index == 17):
            value = 1
        max(0, min(value,1))
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
    
    @Slot()
    def sendPedalMap(self):
        PEDAL_MAP_BASE_ID = 0x0100
        for i in range(2,17):
            if(self.buffers["pedalMap"][i] < self.buffers["pedalMap"][i-1]):
                self.logger.emit("Pedal Map not monotonically increasing! Mapping not sent.")
                return # do not do anything, invalid param
        for i in range(1, 17):                          # indices 1–16 inclusive
            param_id = 0x0006
            QTimer.singleShot(100,lambda param_id=param_id,i=i : self.vcu.set_param(param_id, float(self.buffers["pedalMap"][i]),i))
    
    @Slot()
    def sendMaxTorque(self):
        self.vcu.set_param(0x000F, float(self.window.maxTorque.value()))     # Maximum Torque Request

    @Slot()  
    def show(self):
        self.window.raise_()
        self.window.show()