"""
Overview of thread commands
"""

try:
    from enum import StrEnum  # type: ignore
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class ThreadStatusControl(StrEnum):
    """Commands for `ControlModule.thread_status`, typically from `Hardware.status_sig`."""

    UPDATE_STATUS = "Update_Status"
    CLOSE = "close"
    UPDATE_MAIN_SETTINGS = "update_main_settings"
    UPDATE_SETTINGS = "update_settings"
    RAISE_TIMEOUT = "raise_timeout"
    SHOW_SPLASH = "show_splash"
    CLOSE_SPLASH = "close_splash"


class ThreadStatusMove(StrEnum):
    """Commands for `DAQ_Move.thread_status`, typically from `Hardware.status_sig`."""

    INI_STAGE = "ini_stage"
    GET_ACTUATOR_VALUE = "get_actuator_value"
    CHECK_POSITION = "check_position"
    OUT_OF_BOUNDS = "outofbounds"
    SET_ALLOWED_VALUES = "set_allowed_values"
    STOP = "stop"
    MOVE_DONE = "move_done"


class ThreadStatusViewer(StrEnum):
    """Commands for `DAQ_Viewer.thread_status`, typically from `Hardware.status_sig`."""

    INI_DETECTOR = "ini_detector"
    GRAB = "grab"
    GRAB_STOPPED = "grab_stopped"
    INIT_LCD = "init_lcd"
    LCD = "lcd"
    STOP = "stop"


class QueueHardwareMove(StrEnum):
    """Commands for `DAQ_Move_Hardware.queue_command`, typically from `DAQ_Move.command_hardware`."""

    CLOSE = ThreadStatusControl.CLOSE
    INI_STAGE = ThreadStatusMove.INI_STAGE
    MOVE_ABS = "move_abs"
    MOVE_REL = "move_rel"
    MOVE_HOME = "move_home"
    GET_ACTUATOR_VALUE = "get_actuator_value"
    STOP_MOTION = "stop_motion"
    RESET_STOP_MOTION = "reset_stop_motion"


class QueueTCPControl(StrEnum):
    """Commands for `Listener.queue_command` for a control module, typically from Control._command_tcpip`."""

    UPDATE_CONNECTION = "update_connection"
    SEND_INFO = "send_info"
    CONNECT = "ini_connection"
    QUIT = "quit"


class QueueTCPMove(StrEnum):
    """Commands for `Listener.queue_command` for a move module, typically from Control._command_tcpip`."""

    POSITION = "position_is"
    MOVE_DONE = "move_done"
    X_AXIS = "x_axis"
    Y_AXIS = "y_axis"


class QueueTCPViewer(StrEnum):
    """Commands for `Listener.queue_command` for a viewer module, typically from Control._command_tcpip`."""

    DATA_READY = "data_ready"


class ProcessTCPControl(StrEnum):
    """Commands for `ControlModule.process_tcpip_cmds` for a control module, typically from `Listener.cmd_signal`."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UPDATE_STATUS = "Update_Status"
    LECO_CONNECTED = "leco_connected"
    LECO_DISCONNECTED = "leco_disconnected"
    SET_INFO = "set_info"


class ProcessTCPMove(StrEnum):
    """Commands for `ControlModule.process_tcpip_cmds` for a move module, typically from `Listener.cmd_signal`."""

    MOVE_ABS = QueueHardwareMove.MOVE_ABS
    MOVE_REL = QueueHardwareMove.MOVE_REL
    MOVE_HOME = QueueHardwareMove.MOVE_HOME
    CHECK_POSITION = "check_position"
    GET_ACTUATOR_VALUE = QueueHardwareMove.GET_ACTUATOR_VALUE
    SET_INFO = ProcessTCPControl.SET_INFO


class ProcessTCPViewer(StrEnum):
    """Commands for `ControlModule.process_tcpip_cmds` for a viewer module, typically from `Listener.cmd_signal`."""

    SEND_DATA = "Send Data"
    SET_INFO = ProcessTCPControl.SET_INFO
    GET_AXIS = "get_axis"


class ProcessUiMove(StrEnum):
    """Commands for `DAQ_Move.process_ui_cmds`"""

    INIT = "init"
    QUIT = "quit"
    LOOP_GET_VALUE = "loop_get_value"
    SHOW_LOG = "show_log"
    STOP = "stop"
    SHOW_CONFIG = "show_config"
    REL_VALUE = "rel_value"
    FIND_HOME = "find_home"
    GET_VALUE = "get_value"
    ACTUATOR_CHANGED = "actuator_changed"
    MOVE_ABS = QueueHardwareMove.MOVE_ABS
    MOVE_REL = QueueHardwareMove.MOVE_REL
