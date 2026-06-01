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
        self.txData = [0,0,0,0,0,0,0,0]
        self.txData1 = [0]
        self.dbc = cantools.database.load_file("constants/drew-2-3-0.dbc")

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
    def requestSync(self):
        """Re-emit last-received CFG broadcast values to immediately refresh the UI,
        and mirror them into local CMD state so unsent changes are replaced by VCU truth."""
        for id, signals in self.const.BROADCAST_SIGNALS.items():
            if id >= 0x410:
                for signal in signals:
                    cmd_name = signal[0].replace("DREW_CFG_", "DREW_CMD_")
                    if cmd_name in self.const.CONFIGURATION_SIGNALS:
                        self.const.CONFIGURATION_SIGNALS[cmd_name][1] = signal[1]
                values = [signal[1] for signal in signals]
                try:
                    msg_name = self.dbc.get_message_by_frame_id(id).name
                    self.dataSignal.emit(values, msg_name)
                except Exception:
                    pass

    @Slot()
    def set_param(self, message_name: str):
        msg_def = self.dbc.get_message_by_name(message_name)

        signals = {
            signal.name: self.const.CONFIGURATION_SIGNALS[signal.name][1]
            for signal in msg_def.signals
        }

        data = msg_def.encode(signals, padding=True)

        print(f"[set_param] {message_name} | ID: {msg_def.frame_id:#05x} | signals: {signals} | raw: {data.hex()}")
        super().send_message(
            data=data,
            arbitration_id=msg_def.frame_id,
            is_extended_id=msg_def.is_extended_frame,
            is_fd=msg_def.is_fd
        )
    
    @Slot()
    def writeConfiguration(self):
        super().send_message([], self.const.WRITE_CONFIG_ID, is_extended_id=False)
    @Slot()
    def flashConfiguration(self):
        super().send_message([], self.const.FLASH_CONFIG_ID, is_extended_id=False)
    
    def on_message_received(self, msg):
        self.processMessage(msg)
    
    def processMessage(self, msg):
        if msg.is_error_frame or msg.is_remote_frame:
            return
        if msg.arbitration_id not in self.const.BROADCAST_SIGNALS:
            return

        data = self.dbc.decode_message(msg.arbitration_id, msg.data)
        id = msg.arbitration_id
        signals = self.const.BROADCAST_SIGNALS[id]

        for signal in signals:
            signal[1] = data[signal[0]]