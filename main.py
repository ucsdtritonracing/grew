import can
import sys
import math
from PySide6 import QtWidgets, QtCore
import cantools
import pyqtgraph as pg

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
        simulated = int(10 * math.sin(self.i * 0.1))
        self.i += 1
        signals = {
            "FR_SPEED": simulated,
            "FL_SPEED": simulated + 20,
            "BR_SPEED": simulated + 40,
            "BL_SPEED": simulated + 60
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
    bus = can.interface.Bus(interface='virtual', receive_own_messages=True)
    
    # 2. Instantiate Main Layout Widget and make it visible
    main_widget = MainWidget(bus)
    main_widget.show()  # CRITICAL: Ensures the window actually paints to your desktop
    
    # 3. Setup background CAN configuration 
    db = cantools.database.load_file("constants\\TR-26.dbc")
    msg_def = db.get_message_by_name('WHEEL_STATE')
    
    # 4. Bind listeners using python-can Notifier framework
    listeners = [main_widget.vcu.getListner(), can.Printer()]
    notifier = can.Notifier(bus, listeners)
    
    # 5. Start background simulator to feed virtual data
    simulator = CANSimulators(bus, msg_def)
    
    # 6. Execute Application and ensure clean socket/notifier resource cleanup on close
    exit_code = app.exec()
    notifier.stop()
    bus.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()