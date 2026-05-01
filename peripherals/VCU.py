from peripherals.CANPeripheral import CANPeripheral
from constants.PDUConstants import VCUConstants
from PySide6.QtCore import Slot
import struct
import cantools
    
class PDU(CANPeripheral):
    const = VCUConstants()
    func = lambda self, msg: self.on_message_received(msg)
    def __init__(self, bus):
        super().__init__(id=self.const.DEVICE_ID, isExtended=False, bus=bus, func=self.func)
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
        self.dbc = cantools.database.load_file("constants\TR-26.dbc")
    @Slot()
    def enable(self):
        self.txData1 = [self.const.BROADCAST_ON]
        super().send_message(self, self.txData1, self.const.TOGGLE_BROADCAST_ID)
    @Slot()
    def disable(self):
        self.txData1 = [self.const.BROADCAST_OFF]
        super().send_message(self, self.txData1, self.const.TOGGLE_BROADCAST_ID)
    
    def on_message_recieved(self, msg):
        if(msg.arbitration_id == self.const.RX_PARAMETER_ID):
            if(sum(msg.data[0:7]) % 255 == msg.data[7]):
                self.processMessage(msg)
        elif(msg.arbitration_id <= self.const.BROADCAST_3_ID and msg.arbitration_id >= self.const.BROADCAST_1_ID):
                self.processBroadcast(msg)

    def processMessage(self, msg):
        # see VCU CAN API for data format\

        if(msg.arbitration_id == 0x12A):
            self.state["wheelSpeeds"][0] = struct.unpack('>eeee', msg.data)
        elif(msg.arbitration_id == 0x12B):
            self.state["appsPositions"] = struct.unpack('>ee', msg.data[0:4])
            self.state["bpsPositions"] = struct.unpack('>ee', msg.data[4:8])
        elif(msg.arbitration_id == 0x12C):
            self.state["r2dButtonPressed"] = msg.data[0] & 1 << 7
            self.state["shutdownClosed"] = msg.data[0] & 1 << 6
            # where did all the state variables go >:(
            self.state["sasAngle"] = struct.unpack(">f", msg.data[2:7])
            
        #TODO: for inverter widget, make a state buffer storing state objects so we don't spam update the graph
        #Checksum verified messages below
        if(msg[0] == 0x01):
            if(msg[1] == 0x00):
                value1 = msg[2] << 8 | msg[3] 
                value2 = msg[4] << 8 | msg[5] 
                self.state["apps1RefVolts"] = [value1,value2]
            elif(msg[1] == 0x01):
                value1 = msg[2] << 8 | msg[3] 
                value2 = msg[4] << 8 | msg[5] 
                self.state["apps2RefVolts"] = [value1,value2]
            elif(msg[1] == 0x02):
                value1 = msg[2] == 0xFF
                value2 = msg[3] == 0xFF
                self.state["appsValidity"] = [value1,value2]
        elif(msg[0] == 0x02):
            if(msg[1] == 0x00):
                value1 = msg[2] << 8 | msg[3] 
                value2 = msg[4] << 8 | msg[5] 
                self.state["bpsThresholds"] = [value1,value2]
            elif(msg[1] == 0x01):
                value1 = msg[2] == 0xFF
                value2 = msg[3] == 0xFF
                self.state["bpsValidity"] = [value1,value2]
        elif(msg[0] == 0x03):
            if(msg[1] == 0x00):
                value1 = msg[2] == 0xFF
                self.state["shutdownClosed"] = value1
        elif(msg[0] == 0x04):
            if(msg[1] == 0x00):
                value1 = msg[5] << 24 | msg[4] << 16 | msg[3] << 8 | msg[2]
                self.state["sasAngle"] = value1
        elif(msg[0] == 0x05):
            if(msg[1] == 0x00):
                value1 = msg[2] == 0xFF
                self.state["r2dButtonPressed"] = value1
        elif(msg[0] == 0x06):
            if(msg[1] == 0x00):
                for x in range(0,5):
                    self.state["pedalMap"][x] = msg[x+2]
            elif(msg[1] == 0x01):
                for x in range(5,10):
                    self.state["pedalMap"][x] = msg[x+2]

                
        


                

    