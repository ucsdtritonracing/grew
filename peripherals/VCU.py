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
        self.sync = False
        self._pending_sync_ids = set()
        
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
    def resetUI(self):
        # Group signals by CAN ID, preserving insertion order
        grouped: dict[int, list] = {}
        for signal_name, (can_id, value) in self.const.CONFIGURATION_SIGNALS.items():
            grouped.setdefault(can_id, []).append(value)

        for cmd_id, values in grouped.items():
            cfg_id = cmd_id + 0x100
            try:
                msg_name = self.dbc.get_message_by_frame_id(cfg_id).name
                self.dataSignal.emit(values, msg_name)
            except KeyError:
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

        cfg_echo_id = msg_def.frame_id + 0x100
        if cfg_echo_id in self.const.BROADCAST_SIGNALS:
            if not self.sync:
                self.sync = True
                self._pending_sync_ids = set()
            self._pending_sync_ids.add(cfg_echo_id)
    
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

            if self.sync:
                cmd_name = signal[0].replace("DREW_CFG_", "DREW_CMD_")
                if cmd_name in self.const.CONFIGURATION_SIGNALS:
                    self.const.CONFIGURATION_SIGNALS[cmd_name][1] = signal[1]

        if self.sync and id in self._pending_sync_ids:
            values = [signal[1] for signal in signals]
            msg_name = self.dbc.get_message_by_frame_id(id).name
            self.dataSignal.emit(values, msg_name)

            self._pending_sync_ids.discard(id)
            if not self._pending_sync_ids:
                self.sync = False