from PySide6.QtUiTools import QUiLoader
from functools import partial
from peripherals import Inverter 

class InverterWidget(PeripheralWidget):
    def __init__(self, bus):
        super().__init__(Inverter(bus))
        ui_file = QFile("barebonesMain.ui")
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        window = loader.load(ui_file)
        window.show()