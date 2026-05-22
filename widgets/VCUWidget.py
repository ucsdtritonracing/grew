import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Slot, Signal, QFile
from PySide6.QtUiTools import QUiLoader
from peripherals.VCU import VCU
from functools import partial
class VCUWidget(QtWidgets.QMainWindow):
    def __init__(self, peripheral):
        super().__init__()
        #add ui file loading here
        self.vcu = peripheral
        
        loader = QUiLoader()
        ui_file = QFile("ui\\VCU.ui")
        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file,None)
        ui_file.close()
    
    @Slot()  
    def show(self):
        self.window.raise_()
        self.window.show()