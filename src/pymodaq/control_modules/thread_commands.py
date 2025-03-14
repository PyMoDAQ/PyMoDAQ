from enum import StrEnum


class ThreadStatus(StrEnum):
    """ Allowed Generic commands sent from a plugin using the method: emit_status

    Valid both for DAQ_Move and DAQ_Viewer control modules

    See Also
    --------
    ControlModule.thread_status
    """
    UPDATE_STATUS = 'update_status'
    CLOSE = 'close'
    UPDATE_SETTINGS = 'update_settings'
    UPDATE_MAIN_SETTINGS = 'update_main_settings'
    UPDATE_UI = 'update_ui'
    RAISE_TIMEOUT = 'raise_timeout'
    SHOW_SPLASH = 'show_splash'
    CLOSE_SPLASH = 'close_splash'


class ThreadStatusMove(StrEnum):
    """ Allowed Generic commands sent from a plugin using the method: emit_status

    Valid only for DAQ_Move control module

    See Also
    --------
    DAQ_Move.thread_status
    """
    INI_STAGE = 'ini_stage'
    GET_ACTUATOR_VALUE = 'get_actuator_value'
    MOVE_DONE = 'move_done'
    OUT_OF_BOUNDS = 'outofbounds'
    SET_ALLOWED_VALUES = 'set_allowed_values'
    STOP = 'stop'
    UNITS = 'units'


class ThreadStatusViewer(StrEnum):
    """ Allowed Generic commands sent from a plugin using the method: emit_status

    Valid only for DAQ_Viewer control module

    See Also
    --------
    DAQ_Viewer.thread_status
    """
    INI_DETECTOR = 'ini_detector'
    GRAB = 'grab'
    GRAB_STOPPED = 'grab_stopped'
    INI_LCD = 'init_lcd'
    LCD = 'lcd'
    STOP = 'stop'
