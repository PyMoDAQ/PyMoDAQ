from pymodaq_utils.enums import StrEnum


class ControleModuleType(StrEnum):
    DAQ_MOVE = 'DAQ_Move'
    DAQ_VIEWER = 'DAQ_Viewer'


class ControllerStatus(StrEnum):
    MASTER = 'Master'
    SLAVE = 'Slave'


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
    INI_HARDWARE = 'ini_hardware'   # unified replacement for INI_STAGE / INI_DETECTOR
    STOP = 'stop'                   # unified replacement for ThreadStatusMove.STOP / ThreadStatusViewer.STOP


class ControlToHardware(StrEnum):
    """Commands common to both ActuatorWorker and DetectorWorker workers."""
    INI_HARDWARE = 'ini_hardware'
    CLOSE        = 'close'


class ThreadStatusMove(StrEnum):
    """ Allowed Generic commands sent from a plugin using the method: emit_status

    Valid only for DAQ_Move control module

    See Also
    --------
    DAQ_Move.thread_status
    """
    INI_STAGE = 'ini_stage'         # deprecated: use ThreadStatus.INI_HARDWARE
    GET_ACTUATOR_VALUE = 'get_actuator_value'
    MOVE_DONE = 'move_done'
    OUT_OF_BOUNDS = 'outofbounds'
    SET_ALLOWED_VALUES = 'set_allowed_values'
    STOP = 'stop'                   # deprecated: use ThreadStatus.STOP
    UNITS = 'units'


class ThreadStatusViewer(StrEnum):
    """ Allowed Generic commands sent from a plugin using the method: emit_status

    Valid only for DAQ_Viewer control module

    See Also
    --------
    DAQ_Viewer.thread_status
    """
    INI_DETECTOR = 'ini_detector'   # deprecated: use ThreadStatus.INI_HARDWARE
    GRAB = 'grab'
    GRAB_STOPPED = 'grab_stopped'
    INI_LCD = 'init_lcd'
    LCD = 'lcd'
    STOP = 'stop'                   # deprecated: use ThreadStatus.STOP
    UPDATE_CHANNELS = 'update_channels'



class ControlToHardwareMove(StrEnum):
    """ Allowed commands sent from a DAQ_Move to its ActuatorWorker in another thread
     using the method: command_hardware

    Valid only for DAQ_Move command_hardware commands

    """
    INI_STAGE = 'ini_stage'
    STOP_MOTION = 'stop_motion'
    RESET_STOP_MOTION = 'reset_stop_motion'
    MOVE_ABS = 'move_abs'
    MOVE_REL = 'move_rel'
    MOVE_HOME = 'move_home'
    GET_ACTUATOR_VALUE = 'get_actuator_value'
    CLOSE = 'close'             # deprecated: use ControlToHardware.CLOSE

class ControlToHardwareViewer(StrEnum):
    """ Allowed commands sent from a DAQ_Viewer to its DetectorWorker in another thread
     using the method: command_hardware

    Valid only for DAQ_Viewer command_hardware commands

    """
    INI_DETECTOR = 'ini_detector'

    SINGLE = 'single'
    GRAB = 'grab'
    STOP_GRAB = 'stop_grab'
    ROI_SELECT = 'roi_select'
    UPDATE_SCANNER = 'update_scanner'  # may be deprecated
    CROSSHAIR = 'crosshair'
    UPDATE_WAIT_TIME = 'update_wait_time'
    CLOSE = 'close'             # deprecated: use ControlToHardware.CLOSE


class UiToMainMove(StrEnum):
    """ Allowed Commands to be sent from the DAQ_Move_UI to the DAQ_Move
    """
    INIT = 'init'
    QUIT = 'quit'
    SHOW_LOG = 'show_log'
    SHOW_CONFIG = 'show_config'
    STOP = 'stop'

    MOVE_ABS = 'move_abs'
    MOVE_REL = 'move_rel'

    ACTUATOR_CHANGED = 'actuator_changed'

    GET_VALUE = 'get_value'

    FIND_HOME = 'find_home'
    REL_VALUE = 'rel_value'

    LOOP_GET_VALUE = 'loop_get_value'


class UiToMainViewer(StrEnum):
    """ Allowed Commands to be sent from the DAQ_Viewer_UI to the DAQ_Viewer
    """
    INIT = 'init'
    QUIT = 'quit'
    SHOW_LOG = 'show_log'
    SHOW_CONFIG = 'show_config'
    STOP = 'stop'

    SNAP = 'snap'
    GRAB = 'grab'
    SAVE_CURRENT = 'save_current'
    SAVE_NEW = 'save_new'
    OPEN = 'open'
    RESET_LIVE = 'reset_live'

    DETECTOR_CHANGED = 'detector_changed'
    VIEWERS_CHANGED = 'viewers_changed'

    DO_BKG = 'do_bkg'
    TAKE_BKG = 'take_bkg'