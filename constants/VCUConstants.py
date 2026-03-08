from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class VCUConstants:
    TOGGLE_BROADCAST_ID: int =  0xABA
    RX_PARAMETER_ID: int =      0xCCC
    BROADCAST_1_ID: int =       0x12A
    BROADCAST_2_ID: int =       0x12B
    BROADCAST_3_ID: int =       0x12C
    BROADCAST_ON: int =         0xFF
    BROADCAST_OFF: int =        0x00
    