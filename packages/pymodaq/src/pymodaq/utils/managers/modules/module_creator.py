from qtpy import QtWidgets
from qt_themes import get_theme

from pymodaq_gui.utils import DockArea, Dock

from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.control_modules.enums import DAQTypesEnum
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq.dashboard import DashBoard
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.move_utility_classes import UiType
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq.control_modules.instruments import DET_TYPES, ACTUATOR_TYPES, ACTUATOR_NAMES, find_actuator_class_from_name
from pymodaq_utils.logger import get_module_name, set_logger

config = Config()
logger = set_logger(get_module_name(__file__))


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

    def add_detector(self, detector: DAQ_Viewer):

        # Create compact manager if needed
        if self.dashboard.compact_detector_manager is None:
            self.dashboard.create_compact_detector_manager()
            self.dashboard.compact_detector_manager.show("top")

        # Create individual detector dock
        self.dashboard.docks_viewer.append(Dock(detector.title, size=(350, 350)))
        if self.dashboard.n_docks_viewer == 1:
            self.dashboard.dockarea.addDock(self.dashboard.docks_viewer[-1], "bottom")
            self.dashboard.dockarea.moveDock(self.dashboard.settings_dock, 'right', None)
            self.dashboard.settings_dock.setVisible(False)
            self.dashboard.dockarea.moveDock(self.dashboard.rois_dock, 'right', None)
            self.dashboard.rois_dock.setVisible(False)
            self.dashboard.dockarea.moveDock(self.dashboard.controls_dock, 'right', None)
            self.dashboard.controls_dock.setVisible(False)
        else:
            self.dashboard.dockarea.addDock(self.dashboard.docks_viewer[-1], "right", self._docks_viewer[-2])

        self.dashboard.compact_detector_manager.add_module(detector)
        self.dashboard.docks_viewer[-1].addWidget(detector.parent)
        return detector

    def create_detector(self, name: str, daq_type: DAQTypesEnum) -> DAQ_Viewer:
        widget = QtWidgets.QWidget()

        detector = DAQ_Viewer(
            widget,
            title=name,
            daq_type=daq_type.name,
            settings_dock=self.dashboard.settings_dock,
            rois_dock=self.dashboard.rois_dock,
        )
        try:
            # disconnect the usual route, to add an extra step at init to check around for existing Masters in
            # case one add a Slave after Experiment is set
            detector.do_init_hardware_signal.disconnect()
        except TypeError:
            pass
        detector.do_init_hardware_signal.connect(
            lambda do_init: self.dashboard.modules_manager.on_hardware_initialization(do_init, detector))
        detector.ui.add_action('remove', 'RemoveDetector', 'remove',
                               icon_color=get_theme().blue,
                               toolbar=detector.ui.toolbar, )
        detector.ui.connect_action('remove', lambda: self.remove_detectors([detector]))
        return detector

    def set_detector_type(self, detector: DAQ_Viewer,
                          daq_type: DAQTypesEnum, class_name: str):
        detector.detector = SelectedModule(daq_type, class_name)  # will fire instrument_changed when done

    def _remove_module_list(self, modules: list[DAQ_Move | DAQ_Viewer],
                            module_list: list[DAQ_Move | DAQ_Viewer],
                            compact_manager_attr,
                            remove_dock_widgets=False):
        """Remove a list of control modules, clean up compact manager and docks.

        Parameters
        ----------
        modules: list
            Modules to remove.
        module_list: list
            The dashboard-level list (self.actuators_modules or self.detector_modules)
            from which modules are removed.
        compact_manager_attr: str
            Name of the compact manager attribute on self.
        remove_dock_widgets: bool
            Whether to call dock.removeWidgets() before dock.close() (needed for actuators).
        """
        for module in modules[:]:
            try:
                if module in module_list:
                    module_list.remove(module)
                compact_manager = getattr(self.dashboard, compact_manager_attr)
                if compact_manager:
                    if compact_manager.remove_module(module):
                        compact_manager.close()
                        setattr(self, compact_manager_attr, None)
                module.quit_fun()
                dock = self.dashboard.dockarea.docks.get(module.title, None)
                if dock:
                    self.dashboard.docks_viewer.remove(dock)  # dereference the dock
                    if remove_dock_widgets:
                        dock.removeWidgets()
                    dock.close()
            except Exception as e:
                logger.exception(str(e))

    def remove_detectors(self, detector_modules: list[DAQ_Viewer] = None):
        """
        Remove the given list of detectors from the dashboard.
        Parameters
        ----------
        detector_modules: List[DAQ_Viewer]
            List of DAQ_Viewer instances to be removed.
        """
        if detector_modules is None:
            detector_modules = []
        self._remove_module_list(detector_modules, self.dashboard.detector_modules,
                                 'compact_detector_manager')

    def remove_actuators(self, actuator_modules: list[DAQ_Move] = None):
        """
        Remove the given list of actuators from the dashboard.
        Parameters
        ----------
        actuator_modules: List[DAQ_Move]
            List of DAQ_Move instances to be removed.
        """
        if actuator_modules is None:
            actuator_modules = []
        self._remove_module_list(actuator_modules, self.dashboard.actuators_modules,
                                 'compact_actuator_manager', remove_dock_widgets=True)

    def remove_modules(
            self, modules: list[DAQ_Move | DAQ_Viewer | str] = None,
    ):
        """
        Remove the given list of actuators/detectors from the dashboard.

        Parameters
        ----------
        modules: List[DAQ_Move/DAQ_Viewer]
            List of DAQ_Move/DAQ_Viewer instances to be removed.
        """
        if modules is None:
            modules = []
        try:
            actuators_modules = []
            detector_modules = []
            for module in modules:
                if isinstance(module, DAQ_Move):  # Test if module is an instance of DAQ_Move
                    actuators_modules.append(module)
                elif isinstance(module, DAQ_Viewer):  # Test if module is an instance of DAQ_Viewer
                    detector_modules.append(module)
                if isinstance(module, str):  # Test if module is a string (name of the module)
                    actuators_modules.extend(
                        self.dashboard.modules_manager.get_mods_from_names([module], "act"))  # For actuators

                    detector_modules.extend(
                        self.dashboard.modules_manager.get_mods_from_names([module], "det"),  # For detectors
                    )
            if (hasattr(self.dashboard, "actuators_modules")) & (
                    self.dashboard.actuators_modules is not None
            ):  # Remove actuators
                self.remove_actuators(actuators_modules)
            if (hasattr(self.dashboard, "detector_modules")) & (
                    self.dashboard.detector_modules is not None
            ):  # Remove detectors
                self.remove_detectors(detector_modules)
        except Exception as e:
            logger.exception(str(e))


def build_menu_for_module_creation(masters: list[str]) -> MenuButton:
    master_slave = ['Master', {'Slave of:': masters}]
    actuator_dict = {}
    for act_name in ACTUATOR_NAMES:
        actuator_class = find_actuator_class_from_name(act_name)
        if actuator_class.get_class_axis() is not None and actuator_class.get_class_axis() != ['']:
            axis_dict = {axis: master_slave for axis in actuator_class.get_class_axis()}
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