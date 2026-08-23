from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from pymodaq.control_modules.utils import ControllerAndThread
from pymodaq_gui.parameter import Parameter
from qtpy import QtCore

from pymodaq.control_modules.enums import DAQTypesEnum

from pymodaq.utils.exceptions import MasterSlaveError
from pymodaq.utils.managers.modules import ModuleType

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard

config = GlobalConfig()
logger = set_logger(get_module_name(__file__))


@dataclass()
class PluginInfo:
    id: int
    name: str
    class_name: str
    type: ModuleType
    settings: Parameter | None = None
    is_master: bool = True
    do_init: bool = True
    ui: str | None = None
    daq_type: DAQTypesEnum | None = None
    controller: ControllerAndThread = None


class ModuleLoader(QtCore.QObject):
    """Sequentially create, configure, add and initialize the modules of an experiment.

    Each module goes through the same steps (create -> set type -> add ->
    init -> read controller) before moving on to the next one. The only
    genuinely asynchronous step is hardware initialization, which runs on
    the module's own QThread and reports back through ``init_signal``, so
    each step here waits for the relevant signal rather than polling.

    Any failure while advancing to a module -- whether triggered
    synchronously from :meth:`start` or asynchronously from a module's
    ``init_signal`` fired on its hardware thread -- is reported through
    :attr:`load_failed` instead of being raised, since an exception raised
    from within a slot invoked off the original Python call stack (the
    async case) would not otherwise reach the caller of :meth:`start`.
    """

    all_instruments_added = QtCore.Signal(list)  # list of created Modules
    load_failed = QtCore.Signal(str)
    module_index_init = QtCore.Signal(int, bool)

    def __init__(self, dashboard: 'DashBoard',
                 plugins: list[list['PluginInfo']], parent=None):
        super().__init__(parent)
        self.dashboard = dashboard

        self._queue: list[tuple['PluginInfo', int, int]] = [
            (plugin, ind_in_group, len(group))
            for group in plugins
            for ind_in_group, plugin in enumerate(group)
        ]
        self._ind = -1
        self._current_module: DAQ_Move | DAQ_Viewer = None
        self._modules: list[DAQ_Move | DAQ_Viewer] = []
        self._current_plugin: 'PluginInfo' = None
        self._current_controller: ControllerAndThread = None

        self._init_timeout_timer = QtCore.QTimer()
        self._init_timeout_timer.setInterval(config('pymodaq', 'control_modules', 'control_module_ini_polling') * 1000)
        self._init_timeout_timer.setSingleShot(True)
        self._init_timeout_timer.timeout.connect(self._on_init_timeout)

        self._set_type_timeout_timer = QtCore.QTimer()
        self._set_type_timeout_timer.setInterval(5000)  # wait at most 5 seconds for the ui to update
        self._set_type_timeout_timer.setSingleShot(True)
        self._set_type_timeout_timer.timeout.connect(self._on_set_type_timeout)

    def start(self):
        self._advance()

    def _advance(self):
        self._init_timeout_timer.stop()
        self._set_type_timeout_timer.stop()

        self._ind += 1
        if self._ind == len(self._queue):
            self.all_instruments_added.emit(self._modules)
            return

        try:
            self._process_current()
        except Exception as e:
            logger.exception(str(e))
            self.load_failed.emit(f"Failure while creating the module: {self._current_plugin.name}")

    def _process_current(self):
        plugin_info, ind_in_group, group_size = self._queue[self._ind]
        self._current_plugin = plugin_info
        if plugin_info.controller is not None:  #  else get one from its parent Master
            self._current_controller = plugin_info.controller

        validate_master_slave_order(plugin_info, ind_in_group, group_size)

        if plugin_info.type == ModuleType.Actuator:
            self._current_module = self.dashboard.create_actuator(
                plugin_info.name, plugin_info.class_name, ui_identifier=plugin_info.ui)
        else:
            self._current_module = self.dashboard.create_detector(
                plugin_info.name, plugin_info.daq_type)

        self._modules.append(self._current_module)
        self._current_module.instrument_changed.connect(self._on_type_set)

        self._set_module_type()

    def _on_type_set(self):
        self._set_type_timeout_timer.stop()
        self._current_module.instrument_changed.disconnect(self._on_type_set)

        if self._current_plugin.type == ModuleType.Actuator:
            self.dashboard.add_actuator(self._current_module)
        else:
            self.dashboard.add_detector(self._current_module)

        if not self._current_plugin.do_init:
            # module intentionally left un-initialized (unchecked in the experiment)
            self.module_index_init.emit(self._ind, True)
            self._advance()
            return

        self._current_module.init_signal.connect(self._on_init_done)
        if self._current_plugin.settings is not None:
            self._current_module.apply_controller_parameters(self._current_plugin.settings.child("controller"))
        if not self._current_plugin.is_master:
            self._current_module.controller_and_thread = self._current_controller

        self._init_timeout_timer.start()
        self._current_module.init_hardware_ui()

    def _on_set_type_timeout(self):
        logger.info(f"Timeout reached when attempting setting the type of module: "
                    f"{self._current_plugin.name}/{self._current_plugin.class_name} ")
        self._on_init_done(False)


    def _on_init_done(self, initialized: bool):
        self._init_timeout_timer.stop()
        self._current_module.init_signal.disconnect(self._on_init_done)

        if self._current_plugin.is_master and initialized:
            self._current_controller = self._current_module.controller_and_thread
            self._current_plugin.controller = self._current_controller

        self.module_index_init.emit(self._ind, initialized)

        self._advance()

    def _on_init_timeout(self):
        logger.info(f"Timeout reached when attempting initialization of module: {self._current_plugin.name}")
        self._on_init_done(False)

    def _set_module_type(self):
        self._set_type_timeout_timer.start()
        if self._current_plugin.type == ModuleType.Actuator:
            self.dashboard.set_actuator_type(self._current_module, self._current_plugin.class_name)
        else:
            self.dashboard.set_detector_type(self._current_module,
                                                     self._current_plugin.daq_type,
                                                     self._current_plugin.class_name)
        # transition to _on_type_set happens through the module's own instrument_changed signal


def validate_master_slave_order(plugin_info: 'PluginInfo', ind_in_group: int, group_size: int) -> Any:
    """Check that a plugin's Master/Slave status matches its position within its controller group.

    Raises
    ------
    MasterSlaveError
        if the first plugin of a group isn't Master, if a later one is,
        or if a Master with no init has slaves depending on its controller.
    """
    if ind_in_group == 0:
        if not plugin_info.is_master and plugin_info.controller is None:
            raise MasterSlaveError(f"The instrument {plugin_info.name} without affected controller "
                                   f"should be defined as Master")
        if not plugin_info.do_init and group_size > 1 and plugin_info.is_master:
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} defined as Master has to be "
                f"initialized (init checked in the experiment) in order to init "
                f"its associated slave instrument")
    else:
        if plugin_info.is_master:
            raise MasterSlaveError(f"The instrument {plugin_info.name} should be defined as Slave")
