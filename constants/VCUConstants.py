from dataclasses import dataclass, field
from enum import Enum

@dataclass(frozen=False)
class VCUConstants:
    WRITE_CONFIG_ID: int =  0x301
    FLASH_CONFIG_ID: int =  0x302
    FLASH_ID: int =         0x300
    FLASH_ON: int =         0x01
    FLASH_OFF: int =        0x00
    DEVICE_ID: int =        0x032
    

    BROADCAST_SIGNALS: dict[int, list[list[str | float | int]]] = field(default_factory=lambda: {

        0x12A: [  # DREW_WHEELS
            ["DREW_WSS_FR", 0.0],
            ["DREW_WSS_FL", 0.0],
            ["DREW_WSS_RR", 0.0],
            ["DREW_WSS_RL", 0.0],
        ],

        0x12B: [  # DREW_BSE
            ["DREW_BSEF_Value", 0.0],
            ["DREW_BSEF_Valid", 0],
            ["DREW_BSER_Value", 0.0],
            ["DREW_BSER_Valid", 0],
            ["DREW_BSEF_Raw",   0],
            ["DREW_BSER_Raw",   0],
        ],

        0x12C: [  # DREW_APP
            ["DREW_APP1_Value", 0.0],
            ["DREW_APP1_Valid", 0],
            ["DREW_APP2_Value", 0.0],
            ["DREW_APP2_Valid", 0],
            ["DREW_APP1_Raw",   0],
            ["DREW_APP2_Raw",   0],
        ],

        0x12E: [  # DREW_IMU
            ["DREW_IMU_Yaw",     0],
            ["DREW_IMU_Pitch",   0],
            ["DREW_IMU_Roll",    0],
            ["DREW_IMU_X_Accel", 0.0],
            ["DREW_IMU_Y_Accel", 0.0],
            ["DREW_IMU_Z_Accel", 0.0],
        ],

        0x12F: [  # DREW_FLAGS
            ["DREW_Flags_R2D_Button",  0],
            ["DREW_Flags_SDC_Closed",  0],
            ["DREW_Flags_Fault_APP",   0],
            ["DREW_Flags_Fault_ABPPC", 0],
            ["DREW_Flags_Mode",        0],
        ],

        # ── CFG echo: threshold readback ─────────────────────────────────────────
        0x410: [
            ["DREW_CFG_APP1_Fault_Low",   0.0],
            ["DREW_CFG_APP1_Fault_High",  0.0],
            ["DREW_CFG_APP1_Signal_Low",  0.0],
            ["DREW_CFG_APP1_Signal_High", 0.0],
        ],
        0x411: [
            ["DREW_CFG_APP2_Fault_Low",   0.0],
            ["DREW_CFG_APP2_Fault_High",  0.0],
            ["DREW_CFG_APP2_Signal_Low",  0.0],
            ["DREW_CFG_APP2_Signal_High", 0.0],
        ],
        0x412: [
            ["DREW_CFG_BSEF_Fault_Low",   0.0],
            ["DREW_CFG_BSEF_Fault_High",  0.0],
            ["DREW_CFG_BSEF_Signal_Low",  0.0],
            ["DREW_CFG_BSEF_Signal_High", 0.0],
        ],
        0x413: [
            ["DREW_CFG_BSER_Fault_Low",   0.0],
            ["DREW_CFG_BSER_Fault_High",  0.0],
            ["DREW_CFG_BSER_Signal_Low",  0.0],
            ["DREW_CFG_BSER_Signal_High", 0.0],
        ],

        # ── CFG echo: torque + pedal map ─────────────────────────────────────────
        0x420: [["DREW_CFG_Max_Torque_Request", 0.0]],

        0x430: [["DREW_CFG_Pedal_Map_Point_1",  0.0]],
        0x431: [["DREW_CFG_Pedal_Map_Point_2",  0.0]],
        0x432: [["DREW_CFG_Pedal_Map_Point_3",  0.0]],
        0x433: [["DREW_CFG_Pedal_Map_Point_4",  0.0]],
        0x434: [["DREW_CFG_Pedal_Map_Point_5",  0.0]],
        0x435: [["DREW_CFG_Pedal_Map_Point_6",  0.0]],
        0x436: [["DREW_CFG_Pedal_Map_Point_7",  0.0]],
        0x437: [["DREW_CFG_Pedal_Map_Point_8",  0.0]],
        0x438: [["DREW_CFG_Pedal_Map_Point_9",  0.0]],
        0x439: [["DREW_CFG_Pedal_Map_Point_10", 0.0]],
        0x43A: [["DREW_CFG_Pedal_Map_Point_11", 0.0]],
        0x43B: [["DREW_CFG_Pedal_Map_Point_12", 0.0]],
        0x43C: [["DREW_CFG_Pedal_Map_Point_13", 0.0]],
        0x43D: [["DREW_CFG_Pedal_Map_Point_14", 0.0]],
        0x43E: [["DREW_CFG_Pedal_Map_Point_15", 0.0]],
        0x43F: [["DREW_CFG_Pedal_Map_Point_16", 0.0]],
    })

    CONFIGURATION_SIGNALS: dict[str, list[int | float | int]] = field(default_factory=lambda: {

        # 0x300  DREW_CMD_CONFIGURATION_MODE
        "DREW_CMD_Config_Mode":          [0x300, 0],

        # 0x310  DREW_CMD_APP1_THRESHOLD
        "DREW_CMD_APP1_Fault_Low":       [0x310, 0.0],
        "DREW_CMD_APP1_Fault_High":      [0x310, 0.0],
        "DREW_CMD_APP1_Signal_Low":      [0x310, 0.0],
        "DREW_CMD_APP1_Signal_High":     [0x310, 0.0],

        # 0x311  DREW_CMD_APP2_THRESHOLD
        "DREW_CMD_APP2_Fault_Low":       [0x311, 0.0],
        "DREW_CMD_APP2_Fault_High":      [0x311, 0.0],
        "DREW_CMD_APP2_Signal_Low":      [0x311, 0.0],
        "DREW_CMD_APP2_Signal_High":     [0x311, 0.0],

        # 0x312  DREW_CMD_BSEF_THRESHOLD
        "DREW_CMD_BSEF_Fault_Low":       [0x312, 0.0],
        "DREW_CMD_BSEF_Fault_High":      [0x312, 0.0],
        "DREW_CMD_BSEF_Signal_Low":      [0x312, 0.0],
        "DREW_CMD_BSEF_Signal_High":     [0x312, 0.0],

        # 0x313  DREW_CMD_BSER_THRESHOLD
        "DREW_CMD_BSER_Fault_Low":       [0x313, 0.0],
        "DREW_CMD_BSER_Fault_High":      [0x313, 0.0],
        "DREW_CMD_BSER_Signal_Low":      [0x313, 0.0],
        "DREW_CMD_BSER_Signal_High":     [0x313, 0.0],

        "DREW_CMD_BSEF_Engage":         [0x314,0.0],
        "DREW_CMD_BSER_Engage":         [0x314,0.0],

        # 0x320  DREW_CMD_MAX_TORQUE_REQUEST
        "DREW_CMD_Max_Torque_Request":   [0x320, 0.0],

        # 0x330–0x33F  DREW_CMD_PEDAL_MAP_POINT_1–16
        "DREW_CMD_Pedal_Map_Point_1":    [0x330, 0.0],
        "DREW_CMD_Pedal_Map_Point_2":    [0x331, 0.0],
        "DREW_CMD_Pedal_Map_Point_3":    [0x332, 0.0],
        "DREW_CMD_Pedal_Map_Point_4":    [0x333, 0.0],
        "DREW_CMD_Pedal_Map_Point_5":    [0x334, 0.0],
        "DREW_CMD_Pedal_Map_Point_6":    [0x335, 0.0],
        "DREW_CMD_Pedal_Map_Point_7":    [0x336, 0.0],
        "DREW_CMD_Pedal_Map_Point_8":    [0x337, 0.0],
        "DREW_CMD_Pedal_Map_Point_9":    [0x338, 0.0],
        "DREW_CMD_Pedal_Map_Point_10":   [0x339, 0.0],
        "DREW_CMD_Pedal_Map_Point_11":   [0x33A, 0.0],
        "DREW_CMD_Pedal_Map_Point_12":   [0x33B, 0.0],
        "DREW_CMD_Pedal_Map_Point_13":   [0x33C, 0.0],
        "DREW_CMD_Pedal_Map_Point_14":   [0x33D, 0.0],
        "DREW_CMD_Pedal_Map_Point_15":   [0x33E, 0.0],
        "DREW_CMD_Pedal_Map_Point_16":   [0x33F, 0.0],
    })
    button_map: dict =      field(default_factory=lambda: {
                                "sendApps1SignalButton":"DREW_CMD_APP1_THRESHOLD",
                                "sendBPSHFault":        "DREW_CMD_BSEF_THRESHOLD",                              
                                "sendBPSLFault":        "DREW_CMD_BSEF_THRESHOLD",                               
                                "sendBPSHFault_2":      "DREW_CMD_BSER_THRESHOLD",
                                "sendBPSLFault_2":      "DREW_CMD_BSER_THRESHOLD",
                                "sendApps2SignalButton":"DREW_CMD_APP2_THRESHOLD",
                                "sendBPSFEngaged":      "DREW_CMD_BSE_ENGAGE",
                                "sendBPSREngaged":      "DREW_CMD_BSE_ENGAGE",
                                "sendMaxTorque":        "DREW_CMD_MAX_TORQUE_REQUEST",
                            })