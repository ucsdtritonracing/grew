from dataclasses import dataclass, field
from enum import Enum

@dataclass(frozen=True)
class VCUConstants:
    WRITE_CONFIG_ID: int =  0x194
    FLASH_ID: int =         0x193
    RX_PARAMETER_ID: int =  0x192
    BROADCAST_1_ID: int =   0x12A
    BROADCAST_2_ID: int =   0x12B
    BROADCAST_3_ID: int =   0x12C
    FLASH_ON: int =         0x01
    FLASH_OFF: int =        0x00
    DEVICE_ID: int =        0x067
    SET_PARAM_ID: int =     0x190
    button_map: dict =      field(default_factory=lambda: {
                                "sendAPPSHSignal":      (0x0001, "appsHSignal", 3),
                                "sendAPPSLSignal":      (0x0001, "appsLSignal",2),
                                "sendAPPSHSignal_2":    (0x0002, "appsHSignal_2",3),
                                "sendAPPSLSignal_2":    (0x0002, "appsLSignal_2",2),
                                "sendBPSHFault":        (0x0003, "bpsHFault",1),
                                "sendBPSLFault":        (0x0003, "bpsLFault",0),
                                "sendBPSHFault_2":      (0x0004, "bpsHFault_2",1),
                                "sendBPSLFault_2":      (0x0004, "bpsLFault_2",0),
                                "sendAPPSHFault":       (0x0001, "appsHFault",1),
                                "sendAPPSLFault":       (0x0001, "appsLFault",0),
                                "sendAPPSHFault_2":     (0x0002, "appsHFault_2",1),
                                "sendAPPSLFault_2":     (0x0002, "appsLFault_2",0),
                                "sendBPSFEngaged":      (0x0003, "bpsfEngaged",4),
                                "sendBPSREngaged":      (0x0004, "bpsrEngaged",4),
                            })
    PARAM_NAMES: dict =     field(default_factory=lambda:{
                                0x0000: "INVALID",
                                0x0001: "APP1 Threshold",
                                0x0002: "APP2 Threshold",
                                0x0003: "BSEF Threshold",
                                0x0004: "BSER Threshold",
                                0x0005: "Maximum Torque Request (N.m.)",
                                0x0006: "Pedal Map Point",
                            })