import sys
from PySide6 import QtCore, QtWidgets, QtGui
from peripherals.VCU import VCU
from widgets.PeripheralWidget import PeripheralWidget
from functools import partial
class VCUWidget(PeripheralWidget):
    def __init__(self, bus):
        super.__init__()
        #add ui file loading here