"""
Names of methods used between remotely controlled modules and
remote controlling director modules.
"""

from pymodaq_utils.enums import StrEnum


# Methods for all PyMoDAQ modules
class GenericMethods(StrEnum):
    SET_INFO = "set_info"
    GET_SETTINGS = "get_settings"
    SET_REMOTE_NAME = "set_remote_name"


class MoveMethods(StrEnum):
    MOVE_ABS = "move_abs"
    MOVE_REL = "move_rel"
    MOVE_HOME = "move_home"
    STOP_MOTION = "stop_motion"
    GET_ACTUATOR_VALUE = "get_actuator_value"


class ViewerMethods(StrEnum):
    GRAB = "send_data_grab"
    SNAP = "send_data_snap"
    STOP = "stop_grab"

class DashboardMethods(StrEnum):
    GET_DEVICES = "get_devices"
    GET_CONFIGURATIONS = "get_configurations"
    APPLY_CONFIGURATION = "apply_configuration"
    GET_EXPERIMENTS = "get_experiments"
    APPLY_EXPERIMENT = "apply_experiment"

# Director module methods
class GenericDirectorMethods(StrEnum):
    SET_DIRECTOR_SETTINGS = "set_director_settings"
    SET_DIRECTOR_INFO = "set_director_info"


class MoveDirectorMethods(StrEnum):
    SET_UNITS = "set_units"
    SEND_POSITION = "send_position"
    SET_MOVE_DONE = "set_move_done"

class ViewerDirectorMethods(StrEnum):
    SET_DATA = "set_data"

class DashboardDirectorMethods(StrEnum):
    SEND_DEVICES = "send_devices"
    SEND_CONFIGURATIONS = "send_configurations"
    SEND_EXPERIMENTS = "send_experiments"
    APPLIED_CONFIGURATION_DONE = "applied_configuration_done"
    APPLIED_EXPERIMENT_DONE = "applied_experiment_done"