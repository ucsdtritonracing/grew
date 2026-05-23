from peripherals.CANPeripheral import CANPeripheral
from constants.VCUConstants import VCUConstants
from PySide6.QtCore import Slot, Signal
import cantools
import struct
    
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
             "pedalMap": [0, 0, 0, 0, 0, 0, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 0],
            "wheelSpeeds": [0,0,0,0],
        }
        self.txData = [0,0,0,0,0,0,0,0]
        self.txData1 = [0]
        self.dbc = cantools.database.load_file("constants\\TR-26.dbc")
        
    @Slot()
    def enable(self):
        # enter flash mode 
        self.txData1[0] = [self.const.FLASH_ON]
        super().send_message(self.txData1, self.const.FLASH_ID)
    @Slot()
    def disable(self):
        self.txData1 = [self.const.FLASH_OFF]
        super().send_message(self.txData1, self.const.FLASH_ID)
    
    @Slot()
    def set_param(self, param_id: int, value: float, info: int):
        # Reinterpret the float as its raw IEEE 754 uint32 bit pattern so
        # cantools can pack it into the PARAM_VALUE_FP32 field unchanged.
        raw_fp32 = struct.unpack('<I', struct.pack('<f', value))[0]

        data = self.dbc.encode_message(
            'VCU_SET_PARAM',
            {
                'PARAM_ID':         param_id,
                'PARAM_VALUE_FP32': raw_fp32,
                'PARAM_INFO':       info,
            }
        )
        super().send_message(list(data), self.const.SET_PARAM_ID)
    
    @Slot()
    def writeConfiguration(self):
        super().send_message([], self.const.WRITE_CONFIG_ID)
    
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