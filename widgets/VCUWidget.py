import sys
from PySide6 import QtCore, QtWidgets, QtGui
from peripherals.VCU import VCU
from functools import partial
class VCUWidget(QtWidgets.QMainWindow):
    def __init__(self, bus):
        super.__init__()
        #add ui file loading here