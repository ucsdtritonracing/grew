from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class PDUConstants:
    MOTOR_INFO_ID: int =    165
    TEMPS_ID_1: int =       160
    TEMPS_ID_2: int =       161
    TEMPS_ID_3: int =       162
    STATES_ID: int =        170
    TORQUES_ID: int =       172
    POLE_PAIRS: int =       10
