from typing import Union, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from pymodaq_gui.utils import CustomApp, DockArea
from pymodaq_utils.enums import StrEnum
from pymodaq.utils.managers.modules_manager import ModulesManager

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils.managers.preset.preset_manager import PresetManager
    from pymodaq.utils.managers.configurator.configurator import Configurator


class DashBoardToolbarActions(StrEnum):
    LABEL = 'label'
    SHOW = 'show_dashboard'


class CustomExt(CustomApp):
    status_signal = QtCore.Signal(str)  # signal to be used to emit info
    config_changed = QtCore.Signal()  # will be emitted when the user changed anything in the configuration files (emitted from SharedUI)

    def __init__(self, parent: Union[DockArea, QtWidgets.QWidget, QtWidgets.QMainWindow],
                 dashboard: 'DashBoard', **kwargs):
        super().__init__(parent, **kwargs)

        self.dashboard = dashboard
        self.runner_thread : QtCore.QThread = None
        if dashboard is not None:
            self._modules_manager = ModulesManager(detectors=self.dashboard.detector_modules,
                                                   actuators=self.dashboard.actuators_modules,
                                                   parent_name=self.__class__.__name__)
            if self.preset_manager is not None:
                self.preset_manager.applied_entry.connect(self.do_things_after_preset_set)
                if self.preset_manager.entry_applied:
                    self.do_things_after_preset_set(self.preset_manager.entry)
        else:
            self._modules_manager = None

    def quit_fun(self):
        """Method to be subclassed in order to define a custom quit function
        """
        super().quit_fun()
        if self.dashboard is not None:
            self.show_dashboard(True) #make sure to show it if it was hidden


    def get_main_toolbar(self) -> QtWidgets.QToolBar:
        """ Get the main toolbar widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return self.toolbar

    @property
    def preset_manager(self) -> 'PresetManager':
        if self.dashboard is not None:
            return self.dashboard.preset_manager

    def do_things_after_preset_set(self, preset_name: str):
        """ This method is called whenever a preset entry has been set.

        Its main purpose is to update the list of control modules in the manager and
        some other actions.

        Can be reimplemented to add some more evolved actions
        """
        # update modules manager
        if self.dashboard is not None:
            self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all
            self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all

            # show/hide dashboard
            self.show_dashboard()

    @property
    def configurator(self) -> 'Configurator':
        if self.dashboard is not None:
            return self.dashboard.configurator

    @property
    def splash(self):
        if self.dashboard is not None:
            return self.dashboard.splash_sc

    @property
    def modules_manager(self) -> ModulesManager:
        """useful tool to interact with DAQ_Moves and DAQ_Viewers

        Will be available if a DashBoard has been set

        Returns
        -------
        ModulesManager
        """
        return self._modules_manager

    def exit_runner_thread(self, duration : int = 5000):
        self.runner_thread.quit()
        terminated = self.runner_thread.wait(duration)
        if not terminated:
            self.runner_thread.terminate()
            self.runner_thread.wait()

    def create_dashboard_toolbar(self,
                                 add_preset=True,
                                 add_configurator=True,
                                 add_break=True):
        """ Creates and add a toolbar named dashboard containing means to show/hide the dashboard and optionally
        to display the preset and configurator manager in this toolbar """

        self.add_toolbar('dashboard', 'Dashboard Toolbar',
                         parent=self.mainwindow, add_break=add_break)
        self.add_widget(DashBoardToolbarActions.LABEL, QtWidgets.QLabel('Dashboard:'),
                        toolbar='dashboard')
        self.add_action(DashBoardToolbarActions.SHOW, 'Show Dashboard', 'visibility',
                        'Show/Hide the Dashboard window', checkable=True,
                        icon_color=self.get_theme().green,
                        icon_checked='visibility_off',
                        icon_checked_color=self.get_theme().red,
                        toolbar='dashboard')
        self.get_toolbar('dashboard').addSeparator()
        if add_preset:
            self.preset_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))
            self.get_toolbar('dashboard').addSeparator()
        if add_configurator:
            self.configurator.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))
            self.get_toolbar('dashboard').addSeparator()

        self.connect_action(DashBoardToolbarActions.SHOW, self.show_dashboard)

    def show_dashboard(self, show: bool = None):
        if self.dashboard is not None and self.has_action(DashBoardToolbarActions.SHOW):
            if show is None:
                show = self.is_action_checked(DashBoardToolbarActions.SHOW)
            self.dashboard.mainwindow.setVisible(show)
            self.dashboard.mainwindow.closeEvent = lambda event: self.set_action_checked(DashBoardToolbarActions.SHOW,
                                                                                         False)
