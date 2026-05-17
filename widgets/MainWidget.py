from PySide6.QtUiTools import QUiLoader
from functools import partial
from widgets.PeripheralWidget import PeripheralWidget
from peripherals.Inverter import Inverter
from peripherals.VCU import VCU
from PySide6.QtCore import Slot, Signal, QFile
import pyqtgraph as pg
import time
from collections import deque

class MainWidget(PeripheralWidget):
    def __init__(self, bus):
        self.inverter = Inverter(bus)
        self.vcu = VCU(bus)
        super().__init__()
        
        ui_file = QFile("ui\\carTestingWebappMain.ui")
        ui_file.open(QFile.ReadOnly)
        
        self.inverter.dataSignal.connect(self.updateUI)
        self.vcu.dataSignal.connect(self.updateUI)
        loader = QUiLoader()
        loader.registerCustomWidget(pg.PlotWidget)
        self.window = loader.load(ui_file,self)
        ui_file.close()
        self
        self.setupGraph()


    def setupGraph(self):
        self.start_time = time.perf_counter()
        self.sources = ["Front Right Wheel Speed", "Front Left Wheel Speed", 
                        "Back Right Wheel Speed", "Back Left Wheel Speed"]
        self.buffers = {
            name: {'x': deque(maxlen=500), 'y': deque(maxlen=500)} 
            for name in self.sources
        }
        self.curves = {
            "Front Right Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Front Right Wheel Speed"),
            "Front Left Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Front Left Wheel Speed"),
            "Back Right Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Back Right Wheel Speed"),
            "Back Left Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Back Left Wheel Speed")
        }
        self.viewRange = 10 # default seconds to see


    def updateGraph(self, value, name):
        timestamp = time.perf_counter() - self.start_time
        if name in self.curves:
            # Append new data point to the specific source buffer
            self.buffers[name]['x'].append(timestamp)
            self.buffers[name]['y'].append(value)
            
            # Efficiently update only the modified curve
            self.curves[name].setData(
                list(self.buffers[name]['x']), 
                list(self.buffers[name]['y'])
            )
            self.window.MainGraphWidget.setXRange(timestamp - self.viewRange, timestamp, padding=0)

    def show(self):
        self.window.show()

    @Slot(list, str)
    def updateUI(self, data, name):
        if name == "motor":
            self.updateGraph(data[0],"MOTOR_SPEED")
            self.updateGraph(data[1],"MOTOR_ANGLE")
            self.updateGraph(data[2],"MOTOR_TEMP")
        elif name == "wheelSpeeds":
            self.updateGraph(data[0],"Front Right Wheel Speed")
            self.updateGraph(data[1],"Front Left Wheel Speed")
            self.updateGraph(data[2],"Back Right Wheel Speed")
            self.updateGraph(data[3],"Back Left Wheel Speed")