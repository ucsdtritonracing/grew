from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class VCUConstants:
    WRITE_CONFIG_ID: int =  0x194
    FLASH_ID: int =         0x193
    RX_PARAMETER_ID: int =  0xCCC
    BROADCAST_1_ID: int =   0x12A
    BROADCAST_2_ID: int =   0x12B
    BROADCAST_3_ID: int =   0x12C
    FLASH_ON: int =         0x01
    FLASH_OFF: int =        0x00
    DEVICE_ID: int =        0x067
    SET_PARAM_ID: int =     0x190
    button_map: dict =  {
                            "sendAPPSSignalHigh":   (0x0004, "appsHSignal"),
                            "sendAPPSSignalLow":    (0x0003, "appsLSignal"),
                            "sendAPPSSignalHigh_2": (0x0008, "appsHSignal_2"),
                            "sendAPPSSignalLow_2":  (0x0007, "appsLSignal_2"),
                            "sendBPSFaultHigh":     (0x000A, "bpsHFault"),
                            "sendBPSFaultLow":      (0x0009, "bpsLFault"),
                            "sendBPSFaultHigh_2":   (0x000C, "bpsHFault_2"),
                            "sendBPSFaultLow_2":    (0x000B, "bpsLFault_2"),
                            "sendAPPSFaultHigh":    (0x0002, "appsHFault"),
                            "sendAPPSFaultLow":     (0x0001, "appsLFault"),
                            "sendAPPSFaultHigh_2":  (0x0006, "appsHFault_2"),
                            "sendAPPSFaultLow_2":   (0x0005, "appsLFault_2"),
                            "sendBPSFEngaged":      (0x000D, "bpsfEngaged"),
                            "sendBPSREngaged":      (0x000E, "bpsrEngaged"),
                        }