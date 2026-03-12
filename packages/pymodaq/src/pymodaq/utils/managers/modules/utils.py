from pymodaq_utils.enums import StrEnum


class ModuleType(StrEnum):
    Actuator = "actuator"
    Detector = "detector"
    Other = 'other'
    NONE = 'None'
