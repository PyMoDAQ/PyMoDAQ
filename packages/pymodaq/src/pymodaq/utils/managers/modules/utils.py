from pymodaq_utils.enums import StrEnum


class ModuleType(StrEnum):
    Actuator = "actuator"
    Detector = "detector"
    Control = 'control'  # either actuator or detector
    Other = 'other'
    NONE = 'None'
