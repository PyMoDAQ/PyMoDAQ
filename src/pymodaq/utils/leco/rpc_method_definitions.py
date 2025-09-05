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
