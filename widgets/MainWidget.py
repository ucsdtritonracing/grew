from PySide6.QtUiTools import QUiLoader
from functools import partial
from peripherals.Inverter import Inverter
from peripherals.VCU import VCU
from widgets.VCUWidget import VCUWidget
from PySide6 import QtWidgets
from PySide6.QtCore import Slot, Signal, QFile
import pyqtgraph as pg
import time
from collections import deque
import itertools

class MainWidget(QtWidgets.QMainWindow):
    def __init__(self, peripheral1, peripheral2):
        self.inverter = peripheral1
        self.vcu = peripheral2
        self.vcuWidget = VCUWidget(peripheral2)

        super().__init__()
        
        ui_file = QFile("ui/carTestingWebappMain.ui")
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        loader.registerCustomWidget(pg.PlotWidget)
        self.window = loader.load(ui_file,None)
        ui_file.close()

        
        self.window.VCUConfigButton.clicked.connect(partial(self.vcuWidget.show))
        self.window.VCUConfigButton.clicked.connect(partial(self.vcu.enable))
        self.inverter.dataSignal.connect(self.updateUI)
        self.vcu.dataSignal.connect(self.updateUI)
        self.setupGraph()
        self.window.StartGraphButton.clicked.connect(partial(self.startGraph))
        self.window.StopGraphButton.clicked.connect(partial(self.stopGraph))
        self.window.TimescaleDropdown.currentIndexChanged.connect(partial(self.setRange))
        self.graphEnabled = True

    @Slot()
    def startGraph(self):
        self.graphEnabled = True
    
    @Slot()
    def stopGraph(self):
        self.graphEnabled = False

    @Slot(int)
    def setRange(self, index):
        match index:
            case 0:
                self.viewRange = 5
            case 1: 
                self.viewRange = 10
            case 2: 
                self.viewRange = 30
            case 3:
                self.viewRange = 60
    
    def setupGraph(self):
        self.start_time = time.perf_counter()
        self.sources = ["FRWS", "FLWS", 
                        "BRWS", "BLWS"]
        self.buffers = {
            name: {'x': deque(maxlen=500), 'y': deque(maxlen=500)} 
            for name in self.sources
        }
        
        CURVE_COLORS = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        _color_cycle = itertools.cycle(CURVE_COLORS)

        self.curves = {
            "Front Right Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Front Right Wheel Speed"),
            "Front Left Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Front Left Wheel Speed"),
            "Back Right Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Back Right Wheel Speed"),
            "Back Left Wheel Speed": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Back Left Wheel Speed"),
            "Commanded Torque": self.window.MainGraphWidget.plot(pen=pg.mkPen('r', width=1.5), name="Commanded Torque")
        }


        self.viewRange = 5 # default seconds to see


    def updateGraph(self, value, name):
        timestamp = time.perf_counter() - self.start_time
        if(self.graphEnabled == False):
            return
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
        elif name == "torqueInfo":
            self.updateGraph(data[0],"Commanded Torque")
            
