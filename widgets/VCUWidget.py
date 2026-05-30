import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QTimer, Slot, Signal, QFile
from PySide6.QtUiTools import QUiLoader
from peripherals.VCU import VCU
from functools import partial
import pyqtgraph as pg
import time, math
from collections import deque
from superqt import QLabeledDoubleRangeSlider
from PySide6.QtWidgets import QVBoxLayout

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
            self.setPos(self.fixed_x, 1)
        if(pos.y() > 1):
            self.setPos(self.fixed_x, 1)
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
        ui_file = QFile("ui/VCU.ui")
        ui_file.open(QFile.ReadOnly)
        loader.registerCustomWidget(pg.PlotWidget)
        self.window = loader.load(ui_file,None)
        ui_file.close()
        
        self.setupGraph()
        self.setupApps1RangeSlider()

        self.window.setPedalMapButton.clicked.connect(self.sendPedalMap)
        self.window.sendConfigButton.clicked.connect(self.vcu.writeConfiguration)
        self.window.sendMaxTorque.clicked.connect(self.sendMaxTorque)
        # BPS/APPS threshold buttons
        for btn_name, (param_id, widget_name, info) in self.vcu.const.button_map.items():
            widget = getattr(self.window, widget_name)
            getattr(self.window, btn_name).clicked.connect(
                lambda checked=False, pid=param_id, w=widget, info=info: self.vcu.set_param(pid, float(w.value()),info))
            

        
        
        #self.window.exitConfig.clicked.connect(self.vcu.disable)

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
        value = max(0, min(value,1))
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
        self.vcu.set_param(0x0005, float(self.window.maxTorqueRequest.value()),0)     # Maximum Torque Request

    @Slot()  
    def show(self):
        self.window.raise_()
        self.window.show()
    
    @Slot()
    def setupApps1RangeSlider(self):
        self.apps1FaultSlider = QLabeledDoubleRangeSlider(QtCore.Qt.Vertical)
        #Configure Slider Properties
        self.apps1FaultSlider.setMinimum(0)
        self.apps1FaultSlider.setMaximum(1.0)
        self.apps1FaultSlider.setValue((0.20,0.80)) #initial set
        self.apps1FaultSlider.show()

        self.apps1FaultSlider.setMinimumHeight(250)
        self.apps1FaultSlider.setMinimumWidth(60)

        self.window.appsLSignal.setValue(0.20)
        self.window.appsHSignal.setValue(0.80)


        #Add slider to widget container
        layout = self.window.apps1FaultSliderContainer.layout()
        if layout is None:
            layout = QVBoxLayout(self.window.apps1FaultSliderContainer)
        layout.addWidget(self.apps1FaultSlider)

        #when slider changes call update
        self.apps1FaultSlider.valuesChanged.connect(self.updateApps1FaultSlider)

        #when button clicked send values to vcu
        self.window.sendApps1SignalButton.clicked.connect(self.sendApps1FaultSlider)
        

    @Slot()
    def updateApps1FaultSlider(self,values):
        #get values from the slider
        lowSignal, highSignal = values
        #makes the values into how the vcu shows it
        lowSignal =lowSignal
        highSignal =highSignal
        #update grew locally
        self.vcu.state["apps1Thresholds"][2]= lowSignal
        self.vcu.state["apps1Thresholds"][3]=highSignal
    
    @Slot()
    def updateApps1InputBoxes(self):
        lowSignal = self.window.appsLSignal.value()
        highSignal = self.window.appsHSignal.value()

        #stops triggering connected functions
        #self.apps1FaultSlider.blockSignals(True)
        #sets new slider input values locally
        self.apps1FaultSlider.setValue((lowSignal,highSignal))
        #turns signals back on
        #self.apps1FaultSlider.blockSignals(False)

        self.vcu.state["apps1Thresholds"][2]=lowSignal
        self.vcu.state["apps1Thresholds"][3]=highSignal

    
    @Slot()
    def sendApps1FaultSlider(self):
        #set low and high signal and then send
        lowSignal= self.vcu.state["apps1Thresholds"][2]
        highSignal = self.vcu.state["apps1Thresholds"][3]

        self.vcu.set_param(0x0001,lowSignal ,2)
        self.vcu.set_param(0x0001,highSignal ,3)
    
    @Slot()
    def sendApps1Inputboxes(self):
        lowSignal = self.vcu.state["apps1Thresholds"][2]
        highSignal = self.vcu.state["apps1Thresholds"][3]

        self.vcu.set_param(0x001,lowSignal,2)
        self.vcu.set_param(0x001,highSignal,2)
    @Slot()
    def setupApps2RangeSlider(self):

        self.apps2FaultSlider = QLabeledDoubleRangeSlider(QtCore.Qt.Vertical)
        #Configure Slider Properties
        self.apps2FaultSlider.setMinimum(0)
        self.apps2FaultSlider.setMaximum(100)
        self.apps2FaultSlider.setValue((20,80)) #initial set
        #updateApps1FaultSlider is name of object in PythonCode

        self.window.appsLSignal_2.setValue(0.20)
        self.window.appsHSignal_2.setValue(0.80)

        layout = self.window.apps2FaultSliderContainer.layout()
        layout.addWidget(self.apps2FaultSlider)
        #connects slider to function, wherever the apps slider fault 2 value changes automatically call update
        self.apps2FaultSlider.valuesChanged.connect(self.updateApps2FaultSlider)

    @Slot()
    def updateApps2FaultSlider(self,values):
        #get values from the slider
        lowSignal, highSignal = values
        #makes the values into how the vcu shows it
        lowSignal =lowSignal/100
        highSignal =highSignal/100
        #update grew locally
        self.vcu.state["apps2Thresholds"][2]= lowSignal
        self.vcu.state["apps2Thresholds"][3]=highSignal
    
    @Slot()
    def sendApps2FaultSlider(self):
        #set low and high signal and then send
        lowSignal= self.vcu.state["apps2Thresholds"][2]
        highSignal = self.vcu.state["apps2Thresholds"][3]

        self.vcu.set_param(0x0002,lowSignal ,2)
        self.vcu.set_param(0x0002,highSignal ,3)

        #did i make sure u can send from just inputting, how do i connect inputs to sliders
    @Slot()
    def sendApps2Inputboxes(self):
        lowSignal = self.vcu.state["apps2Thresholds"][2]
        highSignal = self.vcu.state["apps2Thresholds"][3]

        self.vcu.set_param(0x002,lowSignal,2)
        self.vcu.set_param(0x002,highSignal,3)

