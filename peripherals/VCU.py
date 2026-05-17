from peripherals.CANPeripheral import CANPeripheral
from constants.VCUConstants import VCUConstants
from PySide6.QtCore import Slot, Signal
import cantools
    
class VCU(CANPeripheral):
    const = VCUConstants()
    func = lambda self, msg: self.on_message_received(msg)
    dataSignal = Signal(list,str)
    def __init__(self, bus,parent = None):
        super().__init__(id=self.const.DEVICE_ID, isExtended=False, bus=bus, func=self.func, parent = parent)
    def setup(self):
        self.state = {
            "imu": [0,0,0,0,0,0],
            "apps1RefVolts": [0,0],
            "apps2RefVolts": [0,0],
            "appsValidity": [False,False],
            "appsPositions": [0,0],
            "bpsThresholds": [0,0],
            "bpsValidity": [False,False],
            "bpsPositions": [0,0],
            "sasAngle": 0, # recieve from sensor itself 
            "r2dButtonPressed": False,
            "shutdownClosed": False,
            "r2dMode": False,
            "pedalMap": [0,0,0,0,0,0,0,0,0,0],
            "wheelSpeeds": [0,0,0,0],
        }
        self.txData = [0,0,0,0,0,0,0,0]
        self.txData1 = [0]
        self.dbc = cantools.database.load_file("constants\\TR-26.dbc")
        
    @Slot()
    def enable(self):
        self.txData1 = [self.const.BROADCAST_ON]
        super().send_message(self, self.txData1, self.const.TOGGLE_BROADCAST_ID)
    @Slot()
    def disable(self):
        self.txData1 = [self.const.BROADCAST_OFF]
        super().send_message(self, self.txData1, self.const.TOGGLE_BROADCAST_ID)
    
    def on_message_received(self, msg):
        self.processMessage(msg)

    def processMessage(self, msg):
        # see VCU CAN API for data format
        data = self.dbc.decode_message(msg.arbitration_id, msg.data)
        id = msg.arbitration_id
        match id:
            case 298: 
                self.state["wheelSpeeds"][0] = data["FR_SPEED"]
                self.state["wheelSpeeds"][1] = data["FL_SPEED"]
                self.state["wheelSpeeds"][2] = data["BR_SPEED"]
                self.state["wheelSpeeds"][3] = data["BL_SPEED"]
                self.dataSignal.emit(self.state["wheelSpeeds"],"wheelSpeeds")
        
                
        


                

    