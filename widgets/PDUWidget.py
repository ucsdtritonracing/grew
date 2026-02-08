import sys
from PySide6 import QtCore, QtWidgets, QtGui
from peripherals.PDU import PDU
from widgets.PeripheralWidget import PeripheralWidget
from functools import partial
class PDUWidget(PeripheralWidget):
    def __init__(self, bus):
        super().__init__(PDU(bus))

        self.Channel1Off = QtWidgets.QPushButton("CHANNEL 1 OFF")
        self.Channel1Off.clicked.connect(partial(self.peripheral.setCurrentLimit, 1, 0))
        self.Channel1On = QtWidgets.QPushButton("CHANNEL 1 ON")
        self.Channel1On.clicked.connect(partial(self.peripheral.setCurrentLimit, 1, 10))
        self.enable = QtWidgets.QPushButton("ENABLE")
        self.enable.clicked.connect(self.peripheral.enable)
        self.disable = QtWidgets.QPushButton("DISABLE")
        self.disable.clicked.connect(self.peripheral.disable)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.Channel1Off)
        self.layout.addWidget(self.Channel1On)
        self.layout.addWidget(self.enable)
        self.layout.addWidget(self.disable)
        
