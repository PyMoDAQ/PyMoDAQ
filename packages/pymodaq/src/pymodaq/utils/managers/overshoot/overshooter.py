
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import QModelIndex

from pymodaq_data import DataDim
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_data import DataToExport

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

from pymodaq.utils.managers.modules_manager import ModulesManager

from pymodaq.utils.managers.overshoot.utils import PresetScalableGroupOverShoot  # noqa



from pymodaq.utils.config import get_set_config_dir
from pymodaq_gui.managers.manager_base import ManagerBase

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))


def get_set_overshooter_path(subfolder: str = ''):
    """ creates and return the config folder path for overshooter files
    """
    target_path = get_set_config_dir('overshooter_configs').joinpath(subfolder)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


class ModulesManager(ModulesManager):
    """ Customized version of the ModulesManager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.available_data = DataToExport(self.__class__.__name__)

    def get_det_data_list(self) -> DataToExport:
        """Do a snap of selected detectors and get_actuator_value of connected actuators
        , to get the list of all the data and processed data"""

        if len(self.detectors) == 0:
            data_det = DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')
        else:
            self.connect_detectors()
            data_det: DataToExport = self.grab_data()
            self.connect_detectors(False)

        if len(self.actuators) == 0:
            data_act = DataToExport(name=__class__.__name__, control_module='DAQ_Move')
        else:
            self.connect_actuators()
            data_act = self.move_actuators()
            self.connect_actuators(False)

        data_list0D = data_det.get_full_names(DataDim.Data0D)
        data_list0D.extend(data_act.get_full_names(DataDim.Data0D))
        self.settings.child('data_dimensions', 'det_data_list0D').setValue(
            dict(all_items=data_list0D, selected=[]))

        self.available_data = data_list0D[:]
        return data_det


class Overshooter(ManagerBase):
    """
    Main class managing the Overshoots of control modules from a Dashboard and triggers loading
    of a configuration.

    This class provides a GUI to create, modify and save configurations for different overshoots

    Parameters
    ----------

    """

    params = [
        {'title': 'Preset:', 'name': 'preset', 'type': 'str', 'value': ''},
        {'title': 'Overshoots:', 'name': 'overshoots', 'type': 'group_overshoot',},
    ]

    entry_type = 'overshoot'
    entry_extension ='.xml'

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 preset_filename: str = 'default',):

        self._preset_ini = preset_filename

        super().__init__(dashboard=dashboard,
                         module_manager_class=ModulesManager)
        self.preset_filename = preset_filename

        if dashboard is not None:
            self.show_hide_module_manager_settings()
            if self.preset_manager is not None:
                self.preset_manager.applied_entry.connect(self.do_things_after_preset_set)
                if self.preset_manager.entry_applied:
                    self.do_things_after_preset_set(self.preset_manager.entry)
        else:
            self._modules_manager = None

    def show_hide_module_manager_settings(self):

        to_hide = [('move_done',), ('det_done',), ('data_dimensions', 'det_data_list1D'),
                   ('data_dimensions', 'det_data_list2D'),
                   ('data_dimensions', 'det_data_listND'),
                   ('actuators_positions',)]
        for param_tuple in to_hide:
            self.modules_manager.settings.child(*param_tuple).hide()

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        try:
            return get_set_overshooter_path(self.preset_filename)
        except KeyError as e: #fallback to preset ini
            return get_set_overshooter_path(self._preset_ini)

    @property
    def preset_filename(self) -> str:
        if 'preset_filename' not in self.actions_names:
            return self._preset_ini  # fallback at startup
        else:
            return self.get_action('preset_filename').text()

    @preset_filename.setter
    def preset_filename(self, preset_filename: str):
        if preset_filename in [path.stem for path in get_set_preset_path().iterdir()]:
            self._preset_ini = preset_filename
            self.get_action('preset_filename').setText(preset_filename)
            self.entries_sync.update_key('items', self.entries)

    def save_entries(self, entry_path: Path = None):
        pass
        #todo implement this

    # @staticmethod
    # def format_subentries(entries: list[OvershootSubEntry]):
    #     return [(f'{entry.entry_type.capitalize()} for '
    #              f'{entry.module_name} - '
    #              f'{entry.setting.parameter.title()} '
    #              f'{entry.setting.value()}') for entry in entries]

    def execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        config_subentries = config_subentries_from_path(entry_path)

        if len(config_subentries) > 0:
            self.show_subentries(config_subentries, f'Loading Configuration: {self.entry}')

        for ind, entry in enumerate(config_subentries):
            subentry_handler = handler_factory.get_subentry_handler(entry.entry_type)(
                self.overshoot_model, self.settings, self.actuators, self.detectors)
            try:
                if entry.module_name == ModuleType.NONE:
                    mod = None
                else:
                    mod = self.dashboard.modules_manager.get_mod_from_name(
                        entry.module_name, entry.module_type)
                subentry_handler.execute_subentry(entry, module=mod, dashboard=self.dashboard)
                self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(200)
            except SubEntryError as e:
                logger.exception(str(e))
                self.subentries_model.set_status(ind, False)

        self.close_subentries_display(1000)
        return True

    def populate_from_settings(self, settings: Parameter):
        """
        Initialize the configurator from a Parameter settings.

        Parameters
        ----------
        settings : Parameter
            Settings containing all modules configuration
        """
        self.settings = settings
        self.set_readonly_setting(self.settings)
        self.display_settings(display_all=False,
                              param=self.settings)
        self.set_drag_mode_recursive(self.settings, movable=True, drop_enabled=True)

    @property
    def actuators(self):
        return self.modules_manager.actuators_name
    @property
    def detectors(self):
        return self.modules_manager.detectors_name

    def populate_from_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.populate_from_settings(settings)

    def add_subentry(self, special_entry_name: str):
        self.subentry_handler = handler_factory.get_subentry_handler(special_entry_name)(
            self.overshoot_model, self.settings, self.actuators, self.detectors)
        self.subentry_handler.show_dialog()

    def setup_docks(self):
        self.set_toolbar(self.add_toolbar('configurations'))

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        vlayout_right = QtWidgets.QVBoxLayout()
        widget_buttons = QtWidgets.QWidget()
        widget_buttons.setLayout(QtWidgets.QVBoxLayout())
        widget_buttons.layout().addStretch()
        move_toolbar = self.add_toolbar('move')
        move_toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        widget_buttons.layout().addWidget(move_toolbar)
        widget_buttons.layout().addStretch()

        vlayout.addWidget(hwidget)

        hlayout.addWidget(self.modules_manager.settings_tree)

        hlayout.addWidget(widget_buttons)
        hlayout.addLayout(vlayout_right)

        vlayout_right.addWidget(self.get_toolbar('configurations'))
        vlayout_right.addWidget(self.settings_tree)
        self.main_widget.setLayout(vlayout)

    def setup_actions(self):
        self.add_widget('preset_label', QtWidgets.QLabel('Configuration from Preset: '),
                        toolbar=self.get_toolbar('main'))
        self.add_widget('preset_filename', QtWidgets.QLabel(''), tip='Name of the current preset',
                        toolbar=self.get_toolbar('main'))
        self.get_toolbar('main').addSeparator()

    def connect_things(self):


        self.connect_action('show_all_settings', self.display_settings)


    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        if entry.exists():
            self.settings = entry
        else:

            self.settings = Parameter.create(title='Overshoots', name='overshoot',
                                             type='group',
                                             children=self.params)

    def do_things_for_new_creation(self):
        for child in self.settings.child('overshoots').children():
            child.remove()

    def do_things_after_preset_set(self, preset_name: str):
        super().do_things_after_preset_set(preset_name)

        self.modules_manager.selected_actuators_name = self.modules_manager.actuators_name
        self.modules_manager.selected_detectors_name = self.modules_manager.detectors_name


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('PresetManager')
    settings_path = Path(__file__).parent.parent.parent.parent.parent.parent.joinpath('tests/utils/managers/settings.xml')
    external_ui = QtWidgets.QMainWindow()

    shared_ui, dashboard = create_load_dashboard()

    prog = Overshooter(dashboard)

    prog.mainwindow.show()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.enable_actions(True)

    external_ui.show()
    shared_ui.show()

    sys.exit(app.exec())
