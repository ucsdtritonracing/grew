import can
from widgets.PDUWidget import PDUWidget
import sys
from PySide6 import QtWidgets
def __main__():
    app = QtWidgets.QApplication([])
    with can.interface.Bus(interface='virtual', receive_own_messages=True) as bus:
        widgets = {}
        listners = []
        widgets["PDU"] = PDUWidget(bus)
        listners.append(widgets["PDU"].peripheral.getListner())
        print_listener = can.Printer()
        with can.Notifier(bus, listners + [print_listener]) as notifier:
            widgets["PDU"].resize(800, 600)
            widgets["PDU"].show()
            sys.exit(app.exec())

if __name__ == "__main__":
    __main__()
            
            
