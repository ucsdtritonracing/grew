from constants import InverterConstants
from peripherals.CANPeripheral import CANPeripheral
import cantools
from PySide6.QtCore import Slot, Signal
    
class Inverter(CANPeripheral):
    const = InverterConstants()
    func = lambda self, msg: self.on_message_received(msg)
    dataSignal = Signal(list,str)
    def __init__(self, bus):
        super().__init__(id=self.const.DEVICE_ID, isExtended=False, bus=bus, func=self.func)
    def setup(self):
        self.state = {
            "motorInfo":    [0,0,0], #motor speed, motor mechanical angle, motor temp
            "tempInfo":     [0,0,0,0], # A/B/C/control board/
            "torqueInfo":   [0,0,0], # commanded torque, torqueFeedback, torque capability
            "inverterInfo": [False,False,False] # inverter enabled, lockout, forward
        }
        self.db = cantools.database.load_file("constants\20240815_PM_and_RM_CAN_DB.dbc")
        
    @Slot()
    def enable(self):
        #send vcu disable device message here?
        i = 0
    @Slot()
    def disable(self):
        #send vcu enable device message here?
        i = 0
    def processMessage(self, msg):
        data = self.db.decode_message(msg.arbitration_id, msg.data)
        id = msg.arbitration_id
        match id:
            case self.const.MOTOR_INFO_ID:
                self.state["motorInfo"][0] = [data["INV_Motor_Speed"]]
                self.state["motorInfo"][1] = [data["INV_Motor_Angle_Electrical"] / self.const.POLE_PAIRS]
                self.dataSignal.emit(self.state["motorInfo"],"motor")
            case self.const.TEMPS_ID_1:
                self.state["tempInfo"][0] = [data["INV_Module_A"]]
                self.state["tempInfo"][1] = [data["INV_Module_B"]]
                self.state["tempInfo"][2] = [data["INV_Module_C"]]
                self.dataSignal.emit(self.state["tempInfo"])
            case self.const.TEMPS_ID_2:
                self.state["tempInfo"][3] = [data["INV_Control_Board_Temperature"]]
                self.dataSignal.emit(self.state["tempInfo"],"temp")
            case self.const.TEMPS_ID_3:
                self.state["motorInfo"][2] = [data["INV_Motor_Temperature"]]
                self.dataSignal.emit(self.state["motorInfo"],"motor")
            case self.const.STATES_ID:
                self.state["inverterInfo"] = data["INV_Direction_Command"] == 1
                self.state["inverterInfo"] = data["INV_Inverter_Enable_State"] == 1
                self.dataSignal.emit(self.state["inverterInfo"],"inverter")
            case self.const.TORQUES_ID:
                self.state["torqueInfo"][0] = data["INV_Commanded_Torque"]
                self.state["torqueInfo"][1] = data["INV_Torque_Feedback"]
                self.dataSignal.emit(self.state["torqueInfo"],"torque")
                
    
    def on_message_received(self, msg):
        self.processMessage(msg)

    @Slot()
    def shutdown(self):
        super().stop_all_periodics()
        #TODO: send message here to hand over control to VCU
    
    