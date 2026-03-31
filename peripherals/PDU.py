from peripherals.CANPeripheral import CANPeripheral
from constants.PDUConstants import PDUConstants
from PySide6.QtCore import Slot
    
class PDU(CANPeripheral):
    const = PDUConstants()
    func = lambda self, msg: self.on_message_received(msg)
    def __init__(self, bus):
        super().__init__(id=self.const.DEVICE_ID, isExtended=True, bus=bus, func=self.func)
    def setup(self):
        self.state = {
            "requestedCurrentLimit": [0,0,0,0,0,0,0,0],
            "measuredCurrent": [0,0,0,0,0,0,0,0],
            "errorStatus" : [self.const.ERROR.UNKNOWN] * self.const.NUM_CHANNELS
        }
        self.txData = [0,0,0,0,0,0,0,0]
        #TODO: only start periodic when VCU hands over control to laptop
    
    @Slot()
    def enable(self):
        super().start_periodic(self.txData, 0.1, "setCurrentLimit")
    @Slot()
    def disable(self):
        super().stop_periodic("setCurrentLimit")
    
    @Slot()
    def enableVCU(self):
        data = [0xFF,self.const.DEVICE_ID] #0xFF on
        super().send_message(data=data, id=self.const.VCU_COMMAND_ID, isExtended=False)
    
    @Slot()
    def disableVCU(self):
        data = [0x00, self.const.DEVICE_ID] #0x00 off
        super().send_message(data=data, id=self.const.VCU_COMMAND_ID, isExtended=False)

    def processMessage(self, msg, offset):
        channel = offset
        for i in range(0, self.const.NUM_CHANNELS, 2):
            error = (self.const.ERROR_MASK & msg.data[i]) >> 5
            match error:
                case 0x00:
                    self.state["errorStatus"][channel] = self.const.ERROR.OK
                case 0x01:
                    self.state["errorStatus"][channel] = self.const.ERROR.OPEN_CIRCUIT
                case 0x02:
                    self.state["errorStatus"][channel] = self.const.ERROR.SHORT_CIRCUIT
                case 0x03:
                    self.state["errorStatus"][channel] = self.const.ERROR.CURRENT_LIMIT_EXCEEDED
                case _:
                    self.state["errorStatus"][channel] = self.const.ERROR.UNKNOWN
            self.state["measuredCurrent"][channel] = (msg.data[i] << 8 | msg.data[i+1]) & self.const.CURRENT_MASK
            channel += 1
            
    def on_message_received(self, msg):
        channel = 0
        if(msg.arbitration_id == self.const.RX_1_ID):
            self.processMessage(msg, self.const.RX_1_OFFSET)
        elif(msg.arbitration_id == self.const.RX_2_ID):
            self.processMessage(msg, self.const.RX_2_OFFSET)

    @Slot()
    def setCurrentLimit(self, channel, current):
        PDU_MAX_CURRENT = self.const.LOW_LIMIT if self.const.CHANNEL_MASK & (1 << (channel - 1)) else self.const.HIGH_LIMIT
        self.state["requestedCurrentLimit"][channel-1] = min(current, PDU_MAX_CURRENT)
        self.txData[channel-1] = int(round(min(current, PDU_MAX_CURRENT) * self.const.PDU_BIT_TO_POWER_SCALE))
        super().update_periodic("setCurrentLimit", self.txData)
    
    @Slot()
    def stopAllChannels(self):
        self.txData = [0,0,0,0,0,0,0,0]
        self.state["requestedCurrentLimit"] = [0,0,0,0,0,0,0,0]
        # make sure we stop immediately instead of relying on PDU timeout
        super().update_periodic("setCurrentLimit", self.txData) 
        super().stop_periodic("setCurrentLimit")

    @Slot()
    def shutdown(self):
        self.stopAllChannels()
        self.state["measuredCurrent"] = [0,0,0,0,0,0,0,0]
        self.state["errorStatus"] = [self.const.ERROR.UNKNOWN] * self.const.NUM_CHANNELS
        self.state["requestedCurrentLimit"] = [0,0,0,0,0,0,0,0]
        super().stop_all_periodics()
        #TODO: send message here to hand over control to VCU
        #This project is too complicated for the mortal mind :)