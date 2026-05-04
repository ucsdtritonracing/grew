from PySide6 import QtWidgets, QtCore

class PeripheralWidget(QtWidgets.QWidget, QtCore.QObject):
    def __init__(self, peripheral, peripheral1=None):
        super().__init__()
        self.peripheral = peripheral
        self.peripheral1 = peripheral1
    def getPeripheral(self):
        return self.peripheral
    def getPeripheral1(self):
        return self.peripheral1