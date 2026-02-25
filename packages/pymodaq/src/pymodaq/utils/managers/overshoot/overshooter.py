
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_gui.parameter import Parameter, ioxml

from pymodaq.utils.managers.overshoot.utils import ModulesManager, \
    get_set_overshooter_path  # noqa
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))


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
        {'title': 'Preset:', 'name': 'preset', 'type': 'str', 'value': ''},
        {'title': 'Overshoots:', 'name': 'overshoots', 'type': 'group_overshoot'},
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

        to_hide = [('move_done',), ('det_done',),
                   ('data_dimensions', 'probe_data'),
                   ('data_dimensions', 'det_data_list1D'),
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
        """ Particular implementation to save entries for this inherited Manager """

        if entry_path is None:
            entry_path = self.entry_filename

        ioxml.parameter_to_xml_file(
            self.settings,
            entry_path,
            overwrite=True,
        )

    def execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        overshoot_subentries = self.settings.child('overshoots').children()

        if len(overshoot_subentries) > 0:
            self.show_subentries(overshoot_subentries, f'Loading Overshoot: {self.entry}')

        if self.is_action_checked(ManagerActions.EXECUTE):
            pass
        else:
            pass

        for ind, entry in enumerate(overshoot_subentries):
            self.subentries_model.set_status(ind, True)
            QtWidgets.QApplication.processEvents()
            QtCore.QThread.msleep(200)


        self.close_subentries_display(1000)
        return True

    @property
    def actuators(self):
        return self.modules_manager.actuators_name
    @property
    def detectors(self):
        return self.modules_manager.detectors_name

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
        self.add_action('update_data', 'Update Data', 'refresh', toolbar=self.get_toolbar('main'))

    def connect_things(self):
        self.connect_action('update_data', self.update_available_data)

    def update_available_data(self):
        self.modules_manager.get_det_data_list()
        self.settings.child('overshoots').setOpts(addList=self.modules_manager.available_data,
                                                  configurations=self.dashboard.configurator.entries)

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

        self.update_available_data()


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
