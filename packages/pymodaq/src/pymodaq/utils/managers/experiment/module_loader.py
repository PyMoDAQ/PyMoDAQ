from typing import Any, TYPE_CHECKING

from qtpy import QtCore

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.utils.exceptions import MasterSlaveError
from pymodaq.utils.managers.modules.utils import ModuleType

from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager, PluginInfo

logger = set_logger(get_module_name(__file__))


def validate_master_slave_order(plugin_info: 'PluginInfo', ind_in_group: int, group_size: int) -> None:
    """Check that a plugin's Master/Slave status matches its position within its controller group.

    Raises
    ------
    MasterSlaveError
        if the first plugin of a group isn't Master, if a later one is,
        or if a Master with no init has slaves depending on its controller.
    """
    if ind_in_group == 0:
        if not plugin_info.is_master:
            raise MasterSlaveError(f"The instrument {plugin_info.name} should be defined as Master")
        if not plugin_info.do_init and group_size > 1:
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} defined as Master has to be "
                f"initialized (init checked in the experiment) in order to init "
                f"its associated slave instrument")
    else:
        if plugin_info.is_master:
            raise MasterSlaveError(f"The instrument {plugin_info.name} should be defined as Slave")


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

    all_instruments_added = QtCore.Signal()
    load_failed = QtCore.Signal(Exception)

    def __init__(self, manager: 'ExperimentManager', plugins: list[list['PluginInfo']], parent=None):
        super().__init__(parent)
        self.manager = manager

        self._queue: list[tuple['PluginInfo', int, int]] = [
            (plugin, ind_in_group, len(group))
            for group in plugins
            for ind_in_group, plugin in enumerate(group)
        ]
        self._ind = -1
        self._current_module: DAQ_Move | DAQ_Viewer = None
        self._current_plugin: 'PluginInfo' = None
        self._current_controller: Any = None

    def start(self):
        self._advance()

    def _advance(self):
        self._ind += 1
        if self._ind == len(self._queue):
            self.manager.close_subentries_display()
            self.all_instruments_added.emit()
            return

        try:
            self._process_current()
        except Exception as e:
            logger.exception(str(e))
            self.load_failed.emit(e)

    def _process_current(self):
        plugin_info, ind_in_group, group_size = self._queue[self._ind]
        self._current_plugin = plugin_info

        validate_master_slave_order(plugin_info, ind_in_group, group_size)

        if plugin_info.type == ModuleType.Actuator:
            self._current_module = self.manager.dashboard.create_actuator(
                plugin_info.name, plugin_info.class_name, ui_identifier=plugin_info.ui)
            self.manager.actuators_modules.append(self._current_module)
        else:
            self._current_module = self.manager.dashboard.create_detector(
                plugin_info.name, plugin_info.daq_type)
            self.manager.detector_modules.append(self._current_module)

        self._current_module.instrument_changed.connect(self._on_type_set)
        self._set_module_type()

    def _on_type_set(self):
        self._current_module.instrument_changed.disconnect(self._on_type_set)

        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.add_actuator(self._current_module)
        else:
            self.manager.dashboard.add_detector(self._current_module)

        if not self._current_plugin.do_init:
            # module intentionally left un-initialized (unchecked in the experiment)
            self.manager.subentries_model.set_status(self._ind, True)
            self._advance()
            return

        self._current_module.init_signal.connect(self._on_init_done)
        self._current_module.apply_controller_parameters(self._current_plugin.settings.child("controller"))
        if not self._current_plugin.is_master:
            self._current_module.controller = self._current_controller
        self._current_module.init_hardware_ui()

    def _on_init_done(self, initialized: bool):
        self._current_module.init_signal.disconnect(self._on_init_done)

        if self._current_plugin.is_master and initialized:
            self._current_controller = self._current_module.controller
        self.manager.subentries_model.set_status(self._ind, initialized)

        self._advance()

    def _set_module_type(self):
        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.set_actuator_type(self._current_module, self._current_plugin.class_name)
        else:
            self.manager.dashboard.set_detector_type(self._current_module,
                                                     self._current_plugin.daq_type,
                                                     self._current_plugin.class_name)
        # transition to _on_type_set happens through the module's own instrument_changed signal
