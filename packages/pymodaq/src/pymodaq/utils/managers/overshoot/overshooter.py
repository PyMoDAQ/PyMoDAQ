import dataclasses
from typing import Union, TYPE_CHECKING, Callable
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore


from pymodaq_data import DataWithAxes, DataToExport
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_gui.parameter import Parameter, ioxml


from pymodaq.utils.managers.configurator.configurator import Configurator
from pymodaq.utils.managers.preset.preset_manager import PresetManager

from pymodaq.utils.managers.overshoot.utils import ModulesManager, \
    get_set_overshooter_path, TriggerDirection  # noqa
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))

@dataclasses.dataclass
class Overshoot:
    module_name: str
    data_name: str
    channel: str
    direction: TriggerDirection
    value: float
    dwa_value: float = None

    def __repr__(self):
        return f'Data {self.data_name} triggering {self.direction} {self.value}'


class Overshooter(ManagerBase):
    """
    Main class managing the Overshoots of control modules from a Dashboard and triggers loading
    of a configuration.

    This class provides a GUI to create, modify and save configurations for different overshoots

    Parameters
    ----------

    """
    execute_action_checkable = True
    params = [
        {'title': 'Configuration:', 'name': 'configuration', 'type': 'list',
         'limits': [],},
        {'title': 'Overshoots:', 'name': 'overshoots', 'type': 'group_overshoot'},
    ]

    entry_type = 'overshooter'
    entry_extension ='.xml'

    overshoot_signal = QtCore.Signal(Overshoot)

    def __init__(self, dashboard: 'DashBoard'):

        self._configurator = dashboard.configurator

        super().__init__(dashboard=dashboard,
                         module_manager_class=ModulesManager)

        self.slots: dict[str, Callable] = {}

        self._overshoot_under_process = False

        self.overshoot_signal.connect(self.apply_config_from_overshoot)


        self.show_hide_module_manager_settings()

        self.preset_manager.applied_entry.connect(self.do_things_after_preset_set)
        if self.preset_manager.entry_applied:
            self.do_things_after_preset_set(self.preset_manager.entry)
        self.configurator.new_entry.connect(self.update_configurations)
        self.configurator.deleted_entry.connect(self.update_configurations)


    def child_added(self, param: Parameter, data: tuple[Parameter, int]):
        if param is self.settings.child('overshoots'):
            child = data[0]
            child.sigActivated.connect(lambda parameter: child.setValue(not child.value()))

    @property
    def preset_manager(self) -> PresetManager:
        return self.configurator.preset_manager

    @property
    def preset_filename(self) -> str:
        return self.configurator.preset_filename

    @preset_filename.setter
    def preset_filename(self, preset_filename: str):
        self.configurator.preset_filename = preset_filename
        self.entries_sync.update_key('items', self.entries)
        self.update_entry()

    @property
    def configurator(self) -> Configurator:
        return self._configurator

    def apply_config_from_overshoot(self, overshoot: Overshoot):
        self.configurator._execute_entry(
            self.configurator.entry_path_from_name(self.settings['configuration']))
        self._overshoot_under_process = False

    def show_hide_module_manager_settings(self):
        to_hide = [('test_actuator',), ('probe_data',),
                   ]
        for param_tuple in to_hide:
            self.modules_manager.settings.child(*param_tuple).hide()

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_overshooter_path(self.preset_filename)

    def save_entries(self, entry_path: Path = None):
        """ Particular implementation to save entries for this inherited Manager """

        if entry_path is None:
            entry_path = self.entry_filepath

        ioxml.parameter_to_xml_file(
            self.settings,
            entry_path,
            overwrite=True,
        )

    def create_slots(self):
        overshoot_subentries = self.settings.child('overshoots').children()
        self.slots = {}
        for ind, sub_entry in enumerate(overshoot_subentries):
            self.slots[sub_entry.name()] = self.create_slot(sub_entry)

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        overshoot_subentries = self.settings.child('overshoots').children()
        if len(self.slots) == 0:
            self.create_slots()

        if len(overshoot_subentries) > 0:
            if self.is_action_checked(ManagerActions.EXECUTE):
                self.show_subentries(
                    [self.overshoot_from_param(subentry) for subentry in overshoot_subentries],
                    f'Loading Overshoot: {self.entry}')
            for ind, sub_entry in enumerate(overshoot_subentries):
                mod = self.modules_manager.get_mod_from_name(sub_entry['module'])
                if mod is not None:
                    module_type = 'det'
                else:
                    mod = self.modules_manager.get_mod_from_name(sub_entry['module'], 'act')
                    module_type = 'act'

                if mod is not None:
                    if self.is_action_checked(ManagerActions.EXECUTE) and sub_entry.value():
                        if module_type == 'det':
                            mod.grab_done_signal.connect(self.slots[sub_entry.name()])
                        else:
                            mod.current_value_signal.connect(self.slots[sub_entry.name()])
                    else:
                        if module_type == 'det':
                            mod.grab_done_signal.disconnect(self.slots[sub_entry.name()])
                        else:
                            mod.current_value_signal.disconnect(self.slots[sub_entry.name()])
                if self.is_action_checked(ManagerActions.EXECUTE):
                    self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(000)

            if self.is_action_checked(ManagerActions.EXECUTE):
                self.close_subentries_display(1000)
        return True

    def create_slot(self, param: Parameter):
        return lambda dwa: self.process_data(param, dwa)

    def process_data(self, param, data: Union[DataToExport, DataWithAxes]):
        if isinstance(data, DataWithAxes):  # from DAQ_Move modules
            self.process_dwa(param, data)
        elif isinstance(data, DataToExport): # from DAQ_Viewer modules
            self.process_dwa(param, data.get_data_from_name_origin(param['name'],
                                                                   param['module']))
        else:
            pass

    def process_dwa(self, param: Parameter, dwa: DataWithAxes):
        channel_index = dwa.labels.index(param['channel'])
        if not self._overshoot_under_process:
            if param['direction'] == TriggerDirection.ABOVE.name:
                if dwa[channel_index] > param['value']:
                    self._overshoot_under_process = True
                    self.overshoot_signal.emit(self.overshoot_from_param(param, dwa))

            elif param['direction'] == TriggerDirection.BELOW.name:
                if dwa[channel_index] < param['value']:
                    self._overshoot_under_process = True
                    self.overshoot_signal.emit(self.overshoot_from_param(param, dwa))
            else:  # some later cases...
                pass

    def overshoot_from_param(self, param: Parameter, dwa: DataWithAxes = None):
        return Overshoot(param['module'],
                         param['name'],
                         param['channel'],
                         TriggerDirection[param['direction']],
                         param['value'],
                         dwa.value() if dwa is not None else None)

    @property
    def actuators(self):
        return self.modules_manager.actuators_name
    @property
    def detectors(self):
        return self.modules_manager.detectors_name

    def setup_docks(self):
        self.set_toolbar(self.add_toolbar('overshoots'))

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        vlayout_right = QtWidgets.QVBoxLayout()
        vlayout.addWidget(hwidget)

        hlayout.addWidget(self.modules_manager.settings_tree)
        hlayout.addLayout(vlayout_right)

        vlayout_right.addWidget(self.get_toolbar('overshoots'))
        vlayout_right.addWidget(self.settings_tree)
        self.main_widget.setLayout(vlayout)

    def setup_actions(self):
        self.get_toolbar('main').addSeparator()
        self.add_action('update_data', 'Update Data', 'refresh', toolbar=self.get_toolbar('main'))

        self.create_dashboard_toolbar(add_dashboard=__name__ == '__main__',
                                      add_preset=True, add_configurator=True, add_break=False)

    def connect_things(self):
        self.connect_action('update_data', self.update_available_data)

    def update_configurations(self):
        configurations = self.configurator.entries
        self.settings.child('configuration').setLimits(configurations)

    def update_available_data(self):
        self.modules_manager.get_det_data_list()
        self.settings.child('overshoots').setOpts(
            addList=self.modules_manager.available_data)

    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
        if entry is None:
            entry = self.entry_filepath
        elif isinstance(entry, str):
            self.entry = entry
            entry = self.entry_filepath

        if entry.exists():
            self.settings = entry
        else:
            self.settings = Parameter.create(title='Overshoots', name='overshoot',
                                             type='group',
                                             children=self.params)

        self.create_slots()

    def value_changed(self, param: Parameter):
        if self.is_action_checked(ManagerActions.EXECUTE):
            self.get_action(ManagerActions.EXECUTE).trigger()
        self.create_slots()

    def do_things_for_new_creation(self):
        for child in self.settings.child('overshoots').children():
            child.remove()

    def do_things_after_preset_set(self, preset_name: str):
        super().do_things_after_preset_set(preset_name)

        self.modules_manager.selected_actuators_name = self.modules_manager.actuators_name
        self.modules_manager.selected_detectors_name = self.modules_manager.detectors_name

        self.entries_sync.update_key('items', self.entries)
        self._update_entry()
        self.update_available_data()
        self.update_configurations()


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('Overshooter')
    shared_ui, dashboard = create_load_dashboard()
    shared_ui.hide()

    prog = Overshooter(dashboard)
    prog.enable_actions(True)
    prog.mainwindow.show()

    def print_overshoot(overshoot: Overshoot):
        print(overshoot)

    prog.overshoot_signal.connect(print_overshoot)

    sys.exit(app.exec())
