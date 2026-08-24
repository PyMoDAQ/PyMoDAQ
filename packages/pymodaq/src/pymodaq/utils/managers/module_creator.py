from qtpy import QtWidgets
from qt_themes import get_theme

from pymodaq_utils.config import GlobalConfig as Config

from pymodaq.dashboard import DashBoard
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.move_utility_classes import UiType
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq.control_modules.instruments import DET_TYPES, ACTUATOR_TYPES, ACTUATOR_NAMES, find_actuator_class_from_name

config = Config()


class ModuleCreator:

    def __init__(self, dashboard: DashBoard):
        self.dashboard = dashboard
        self.menu_button: MenuButton = None

        self.create_menu_to_add_modules()

        self.menu_button.triggered.connect(self._add_module)

    def create_menu_to_add_modules(self) -> MenuButton:
        masters = [mod for mod in self.dashboard.modules_manager.modules_all if mod.master]
        self.menu_button = build_menu_for_module_creation(masters)
        return self.menu_button

    def _add_module(self, path: tuple[str]):
        pass

    def create_actuator(self, name: str, class_name: str, ui_identifier: str) -> DAQ_Move:
        actuator_class = find_actuator_class_from_name(class_name)
        forced_ui = actuator_class.ui_type
        ui_identifier = forced_ui if forced_ui != UiType.NONE else ui_identifier

        if ui_identifier is not None:
            pass
        else:
            ui_identifier = config("pymodaq", "actuator", "ui")
        actuator = DAQ_Move(QtWidgets.QWidget(),
                            name,
                            ui_identifier=ui_identifier,
                            settings_dock=self.dashboard.settings_dock,
                            controls_dock=self.dashboard.controls_dock,
                            )
        actuator.bounds_signal[bool].connect(self.dashboard.do_stuff_from_out_bounds)
        try:
            # disconnect the usual route, to add an extra step at init to check around for existing Masters in
            # case one add a Slave after Experiment is set
            actuator.do_init_hardware_signal.disconnect()
        except TypeError:
            pass
        actuator.do_init_hardware_signal.connect(
            lambda do_init: self.dashboard.modules_manager.on_hardware_initialization(do_init, actuator))

        actuator.ui.add_action('remove', 'RemoveActuator', 'remove', icon_color=get_theme().blue,
                               toolbar=actuator.ui.toolbar,)
        actuator.ui.connect_action('remove', lambda: self.remove_actuators([actuator]))

        return actuator

    def set_actuator_type(self, actuator: DAQ_Move, class_name: str):
        actuator.actuator = class_name  # will fire instrument_changed when done

    def add_actuator(self, actuator: DAQ_Move):
        # Create compact manager if needed
        if self.dashboard.compact_actuator_manager is None:
            self.dashboard.create_compact_actuator_manager()
            if self.dashboard.compact_detector_manager is not None:
                self.dashboard.compact_actuator_manager.show(
                    'bottom', self.dashboard.compact_detector_manager.dock)
            else:
                self.dashboard.compact_actuator_manager.show("top")

        QtWidgets.QApplication.processEvents()

        self.dashboard.compact_actuator_manager.add_module(actuator)
        return actuator





def build_menu_for_module_creation(masters: list[str]) -> MenuButton:
    master_slave = ['Master', {'Slave of:': masters}]
    actuator_dict = {}
    for act_name in ACTUATOR_NAMES:
        actuator_class = find_actuator_class_from_name(act_name)
        if actuator_class._axis_names is not None and actuator_class._axis_names != ['']:
            axis_dict = {axis: master_slave for axis in actuator_class._axis_names}
        else:
            axis_dict = master_slave
        actuator_dict[act_name] = axis_dict

    detector_options = {
        'DAQ0D': [{name: master_slave} for name in [plugin['name'] for plugin in DET_TYPES['DAQ0D']]],
        'DAQ1D': [{name: master_slave} for name in [plugin['name'] for plugin in DET_TYPES['DAQ1D']]],
        'DAQ2D': [{name: master_slave} for name in [plugin['name'] for plugin in DET_TYPES['DAQ2D']]],
        'DAQND': [{name: master_slave} for name in [plugin['name'] for plugin in DET_TYPES['DAQND']]],
    }

    menu_entries = {'Actuators:': actuator_dict,
                    'Detectors:': detector_options, }

    return MenuButton(text='AddModule',
                      add_menu_entries=menu_entries,
                      update_button_text=False)


if __name__ == '__main__':
    import sys
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Selector')


    def print_path(path: tuple[str]):
        print(path)


    button = build_menu_for_module_creation(masters=['act0', 'act1', 'act2'], )
    button.triggered.connect(print_path)
    button.show()

    sys.exit(app.exec())