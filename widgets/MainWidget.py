from PySide6.QtUiTools import QUiLoader
from functools import partial
from widgets import PeripheralWidget
from peripherals import Inverter, VCU
from PySide6.QtCore import Slot, Signal, QFile

class MainWidget(PeripheralWidget):
    def __init__(self, bus):
        super().__init__(VCU(bus),Inverter(bus))
        inverter = super().getPeripheral()
        vcu = super().getPeripheral1()
        ui_file = QFile("barebonesMain.ui")
        ui_file.open(QFile.ReadOnly)

        inverter.dataSignal.connect(self.updateUI)
        vcu.dataSignal.connect(self.updateUI)
        loader = QUiLoader()
        window = loader.load(ui_file)
        window.show()
    
    @Slot(list)
    def updateUI(self, data, name):
        #update ui data here
        i = 0
    

    

