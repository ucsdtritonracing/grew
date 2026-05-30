import can
import sys
import math
from PySide6 import QtWidgets, QtCore
import cantools
import pyqtgraph as pg
from peripherals.Inverter import Inverter
from peripherals.VCU import VCU
from can.interfaces.pcan import PcanBus
from can import BusState
import random

# Dummy wrapper assuming MainWidget loads your UI layout internally
from widgets.MainWidget import MainWidget 

class CANSimulators(QtCore.QObject):
    """Sends periodic mock CAN frames to simulate wheel speed streaming."""
    def __init__(self, bus, msg_def):
        super().__init__()
        self.bus = bus
        self.msg_def = msg_def
        self.i = 0
        
        # QTimer for background data transmission (10Hz / every 100ms)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.send_mock_frame)
        self.timer.start(100)

    def send_mock_frame(self):
        simulated = int(5 * random.random() * math.sin(self.i*random.randint(1,10) * 0.1))
        self.i += 1
        signals = {
            "FR_SPEED": simulated,
            "FL_SPEED": simulated + random.randint(10,15),
            "BR_SPEED": simulated + random.randint(20,30) * math.fabs(math.sin(0.1*self.i)) ,
            "BL_SPEED": simulated + random.randint(30,33)
        }
        msg_data = self.msg_def.encode(signals)
        can_msg = can.Message(
            arbitration_id=self.msg_def.frame_id,
            data=msg_data,
            is_extended_id=self.msg_def.is_extended_frame
        )
        try:
            self.bus.send(can_msg)
        except can.CanError:
            pass

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # 1. Initialize CAN Bus interface
    bus = can.interface.Bus(
        interface='virtual',
        channel='PCAN_USBBUS1',
        bitrate=500000,        # match exactly what the VCU firmware is configured for
        receive_own_messages=True,
    )
    #bus = can.interfaces.pcan.PcanBus(channel='PCAN_USBBUS1', timing=timing, bitrate=500000, receive_own_messages=False)
    #print(bus.status_string())
    inverter = Inverter(bus)
    vcu = VCU(bus)
    # 2. Instantiate Main Layout Widget and make it visible
    main_widget = MainWidget(inverter,vcu)
    main_widget.show()  # CRITICAL: Ensures the window actually paints to your desktop
    
    # 3. Setup background CAN configuration 
    db = cantools.database.load_file("constants/TR-26.dbc")
    msg_def = db.get_message_by_name('WHEEL_STATE')
    msg = db.get_message_by_name('VCU_SET_PARAM')
    print(f"is_fd={msg.is_fd}, is_extended={msg.is_extended_frame}")
    # 4. Bind listeners using python-can Notifier framework
    listeners = [vcu.getListner(),inverter.getListner(), can.Printer()] 
    notifier = can.Notifier(bus, listeners)
    
    # 5. Start background simulator to feed virtual data
    #simulator = CANSimulators(bus, msg_def)
#    print(bus.status_string())
    # 6. Execute Application and ensure clean socket/notifier resource cleanup on close
    exit_code = app.exec()
    notifier.stop()
    bus.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()