from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class InverterConstants:
    MOTOR_INFO_ID: int =    165
    TEMPS_ID_1: int =       160
    TEMPS_ID_2: int =       161
    TEMPS_ID_3: int =       162
    STATES_ID: int =        170
    TORQUES_ID: int =       172
    FAULTS_ID: int =        171
    POLE_PAIRS: int =       10
    DEVICE_ID: int = 0x067
    faults_dict = {
        0: "Motor Over-speed Fault",
        1: "Over-current Fault",
        2: "Over-voltage Fault",
        3: "Inverter Over-temperature Fault",
        4: "Accelerator Input Shorted Fault",
        5: "Accelerator Input Open Fault",
        6: "Direction Command Fault",
        7: "Inverter Response Time-out Fault",
        8: "Hardware Gate/Desaturation Fault",
        9: "Hardware Over-current Fault",
        10: "Under-voltage Fault",
        11: "CAN Command Message Lost Fault",
        12: "Motor Over-temperature Fault",
        16: "Brake Input Shorted Fault",
        17: "Brake Input Open Fault",
        18: "Module A Over-temperature Fault",
        19: "Module B Over-temperature Fault",
        20: "Module C Over-temperature Fault",
        21: "PCB Over-temperature Fault",
        22: "Gate Drive Board 1 Over-temperature Fault",
        23: "Gate Drive Board 2 Over-temperature Fault",
        24: "Gate Drive Board 3 Over-temperature Fault",
        25: "Current Sensor Fault",
        26: "Gen 5: Gate Driver Over-Voltage",
        27: "Gen 3: Hardware DC Bus Over-Voltage Fault",
        28: "Gen 5: Hardware DC Bus Over-voltage Fault",
        30: "Resolver Not Connected"
    }
