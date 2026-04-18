from peripherals.CANPeripheral import CANPeripheral
from constants.PDUConstants import PDUConstants
from PySide6.QtCore import Slot
import cantools
    
class PDU(CANPeripheral):
    const = PDUConstants()
    func = lambda self, msg: self.on_message_received(msg)
    def __init__(self, bus):
        super().__init__(id=self.const.DEVICE_ID, isExtended=True, bus=bus, func=self.func)
    def setup(self):
        self.state = {
            "requestedCurrentLimit": [0,0,0,0,0,0,0,0], # only tracks grew commands
            "measuredCurrent": [0,0,0,0,0,0,0,0],
            "errorStatus" : [self.const.ERROR.UNKNOWN] * self.const.NUM_CHANNELS
        }
        self.txData = [0,0,0,0,0,0,0,0]
        self.db = cantools.database.load_file("constants\AEM 30-8300 PDU-8 20200616.dbc")
    
    @Slot()
    def enable(self):
        super().start_periodic(self.txData, 0.1, "setCurrentLimit")
    @Slot()
    def disable(self):
        super().stop_periodic("setCurrentLimit")
    
    def processMessage(self, msg):
        temp = self.db.decode_message(msg.arbitration_id, msg.data)
        if(msg.arbitration_id == self.const.RX_1_ID):
            for i in range(1, self.const.RX_2_OFFSET + 1):
                self.state["errorStatus"][i-1] = self.const.ERROR(temp[f"PDMErrorStatus0{i}"])
                self.state["measuredCurrent"][i-1] = temp["PDMMeasuredCurrent0{i}"]
        elif(msg.arbitration_id == self.const.RX_2_ID):
            for i in range(self.const.RX_2_OFFSET + 1, self.const.NUM_CHANNELS + 1):
                self.state["errorStatus"][i-1] = self.const.ERROR(temp[f"PDMErrorStatus0{i}"])
                self.state["measuredCurrent"][i-1] = temp[f"PDMMeasuredCurrent0{i}"]

    def on_message_received(self, msg):
        self.processMessage(msg)

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