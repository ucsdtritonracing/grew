from dataclasses import dataclass
import dataclasses as data
from enum import Enum
from typing import ClassVar

@dataclass(frozen=True)
class PDUConstants:
    VCU_COMMAND_ID: int =                   0x00676767
    ENABLE_FRAME: ClassVar[list[int]] =     [0x67,0x67,0x67,0x67,0x0,0x0,0x0,0x0]
    DISABLE_FRAME: ClassVar[list[int]] =    [0x0,0x0,0x0,0x0,0x67,0x67,0x67,0x67]
    RX_1_ID: int =                          0x000A0610
    RX_2_ID: int =                          0x000A0611
    DEVICE_ID: int =                        0x000A0620
    ERROR_MASK: int =                       0b11100000
    CURRENT_MASK: int = 	                0b0000001111111111
    NUM_CHANNELS: int =                     8
    RX_1_OFFSET: int =                      0
    RX_2_OFFSET: int =                      4
    PDU_BIT_TO_POWER_SCALE: float =         2.5
    CHANNEL_MASK: int =                     0b01100110
    HIGH_LIMIT: int = 		                20
    LOW_LIMIT: int = 		                10
    class ERROR(Enum):      
        OK =                                "OK"
        OPEN_CIRCUIT =                      "OPEN_CIRCUIT"
        SHORT_CIRCUIT =                     "SHORT_CIRCUIT"
        CURRENT_LIMIT_EXCEEDED =            "CURRENT_LIMIT_EXCEEDED"
        UNKNOWN =                           "UNKNOWN"