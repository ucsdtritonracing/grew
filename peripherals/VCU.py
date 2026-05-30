from peripherals.CANPeripheral import CANPeripheral
from constants.VCUConstants import VCUConstants
from PySide6.QtCore import Slot, Signal
import cantools
import struct
    
class VCU(CANPeripheral):
    const = VCUConstants()
    func = lambda self, msg: self.on_message_received(msg)
    dataSignal = Signal(list,str)
    logger = Signal(str)
    def __init__(self, bus,parent = None):
        super().__init__(id=self.const.DEVICE_ID, isExtended=False, bus=bus, func=self.func, parent = parent)
    def setup(self):
        self.state = {
            "imu": [0,0,0,0,0,0],
            "apps1Thresholds": [0,0,0,0],
            "apps2Thresholds": [0,0,0,0],
            "appsValidity": [False,False],
            "appsPositions": [0,0],
            "bpsfThresholds": {0:0,1:0,4:0},
            "bpsrThresholds": {0:0,1:0,4:0},
            "bpsValidity": [False,False],
            "bpsPositions": [0,0],
            "sasAngle": 0, # recieve from sensor itself
            "maxTorqueRequest": 0, 
            "r2dButtonPressed": False,
            "shutdownClosed": False,
            "r2dMode": False,
            "pedalMap": [0, 0, 0, 0, 0, 0, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 0],
            "wheelSpeeds": [0,0,0,0],
            
        }
        self.txData = [0,0,0,0,0,0,0,0]
        self.txData1 = [0]
        self.dbc = cantools.database.load_file("constants\\drew-2-2-1.dbc")
        
    @Slot()
    def enable(self):
        # enter flash mode 
        print("HI IM ENABLED")
        self.txData1[0] = self.const.FLASH_ON
        super().send_message(self.txData1, self.const.FLASH_ID, is_extended_id=False)
    @Slot()
    def disable(self):
        self.txData1 = [self.const.FLASH_OFF]
        super().send_message(self.txData1, self.const.FLASH_ID, is_extended_id=False)
    
    @Slot()
    def set_param(self, param_id: int, value: float, info: int):
        msg_def = self.dbc.get_message_by_name('VCU_SET_PARAM')
        
        # 2. Encode signals to raw bytes (keep as a bytes object)
        data = msg_def.encode({
            'PARAM_ID':         param_id,
            'PARAM_VALUE_FP32': value,
            'PARAM_INFO':       info,
        },padding=True)
        
        # 3. Pass the DBC's metadata properties directly to the sender
        super().send_message(
            data=data, 
            arbitration_id=msg_def.frame_id, 
            is_extended_id=msg_def.is_extended_frame,
            is_fd=msg_def.is_fd
        )
    
    @Slot()
    def writeConfiguration(self):
        super().send_message([], self.const.WRITE_CONFIG_ID, is_extended_id=False)
    
    def on_message_received(self, msg):
        if(msg.arbitration_id == self.const.RX_PARAMETER_ID):
            param = self.processParam(msg)
            match param[0]:
                case 0x001:
                    if(self.state["apps1Thresholds"][param[1]] != param[2]):
                        self.logger.emit(f"apps1 param index {param[1]} desynced (vcu:{param[2]}!=grew:{self.state["apps1Thresholds"][param[1]]})")
                case 0x002:
                    if(self.state["apps2Thresholds"][param[1]] != param[2]):
                        self.logger.emit(f"apps2 param index {param[1]} desynced (vcu:{param[2]}!=grew:{self.state["apps2Thresholds"][param[1]]})")
                case 0x003:
                    if(self.state["bpsfThresholds"][param[1]] != param[2]):
                        self.logger.emit(f"bpsf param index {param[1]} desynced (vcu:{param[2]}!=grew:{self.state["bpsfThresholds"][param[1]]})")
                case 0x004:
                    if(self.state["bpsrThresholds"][param[1]] != param[2]):
                        self.logger.emit(f"bpsr param index {param[1]} desynced (vcu:{param[2]}!=grew:{self.state["bpsrThresholds"][param[1]]})")
                case 0x005:
                    if(self.state["maxTorqueRequest"] != param[2]):
                        self.logger.emit(f"maxTorqueRequest desynced (vcu:{param[2]}!=grew:{self.state["maxTorqueRequest"]})")
                case 0x006:
                    if(self.state["pedalMap"][param[1]] != param[2]):
                        self.logger.emit(f"pedalMap param index {param[1]} desynced (vcu:{param[2]}!=grew:{self.state["pedalMap"][param[1]]})")
        else:
            #self.processMessage(msg)
            pass

    def processParam(self, msg):
        data = self.dbc.decode_message(msg.arbitration_id, msg.data)

        param_id = int(data["PARAM_ID"])
        param_info = int(data["PARAM_INFO"])
        param_value = data["PARAM_VALUE_FP32"]

        param_name = self.const.PARAM_NAMES.get(param_id, f"UNKNOWN (0x{param_id:04X})")

        return (param_name, param_info, param_value)
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