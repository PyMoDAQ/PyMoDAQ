"""Everything an object needs to work with a DashBoard.

Shared by the extensions (:class:`~pymodaq.utils.custom_ext.CustomExt`) and by the managers needing
the dashboard (:class:`~pymodaq.utils.managers.manager_with_dashboard.ManagerWithDashboard`).
It lives in ``pymodaq`` because the lower packages (``pymodaq_gui``...) must not import it.
"""
from typing import Union, TYPE_CHECKING

from pymodaq_utils.enums import StrEnum

from pymodaq.utils.managers.modules.modules_manager import ModulesManager

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
    from pymodaq.utils.managers.state.state_manager import StateManager


class DashBoardToolbarActions(StrEnum):
    LABEL = 'label'
    SHOW = 'show_dashboard'


class DashboardMixin:
    """ Gives access to the dashboard and to a ModulesManager built on its control modules

    To be placed *before* a :class:`~pymodaq_gui.utils.custom_app.CustomApp` (or subclass) in the
    bases, for instance ``class MyExt(DashboardMixin, CustomApp)``. The dashboard is set (together
    with the modules manager) before the other bases are initialized, so it is available in
    ``setup_ui`` and the like. The connection to the experiment manager (and the first call of
    ``do_things_after_experiment_set``) is done once the whole object is built.
    """

    def __init__(self, *args, dashboard: 'DashBoard' = None,
                 module_manager_class=ModulesManager, **kwargs):
        self.dashboard = dashboard

        if dashboard is not None:
            self._modules_manager = module_manager_class(
                detectors=dashboard.detector_modules,
                actuators=dashboard.actuators_modules,
                parent_name=self.__class__.__name__)
        else:
            self._modules_manager = None

        super().__init__(*args, **kwargs)

        if dashboard is not None and self.experiment_manager is not None:
            self.experiment_manager.applied_entry.connect(self.do_things_after_experiment_set)
            if self.experiment_manager.entry_applied:
                self.do_things_after_experiment_set(self.experiment_manager.entry)

    @property
    def experiment_manager(self) -> Union['ExperimentManager', None]:
        if self.dashboard is not None:
            return self.dashboard.experiment_manager

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        """ This method is called whenever an experiment entry has been set.

        Its main purpose is to update the list of control modules in the manager and
        some other actions.

        Can be reimplemented to add some more evolved actions
        """
        # update modules manager
        if self.dashboard is not None:
            self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all
            self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all

            # show/hide dashboard
            self.show_dashboard(show_dashboard)

    @property
    def state_manager(self) -> 'StateManager':
        if self.dashboard is not None:
            return self.dashboard.state_manager

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

    def create_dashboard_toolbar(self,
                                 add_dashboard: bool = True,
                                 add_experiment=True,
                                 add_state=True,
                                 add_break=True):
        """ Creates and add a toolbar named dashboard containing means to show/hide the dashboard and optionally
        to display the experiment and state manager in this toolbar """

        self.add_toolbar('dashboard', 'Dashboard Toolbar',
                         parent=self.mainwindow, add_break=add_break)
        if add_dashboard:
            # self.add_widget(DashBoardToolbarActions.LABEL, QtWidgets.QLabel('Dashboard:'),
            #                 toolbar='dashboard')
            self.add_action(DashBoardToolbarActions.SHOW, 'Show Dashboard', 'visibility',
                            'Show/Hide the Dashboard window', checkable=True,
                            icon_color=self.get_theme().green,
                            icon_checked='visibility_off',
                            icon_checked_color=self.get_theme().red,
                            toolbar='dashboard')
            self.get_toolbar('dashboard').addSeparator()
            self.connect_action(DashBoardToolbarActions.SHOW, self.show_dashboard)

        if add_experiment:
            self.experiment_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))
            self.get_toolbar('dashboard').addSeparator()
        if add_state:
            self.state_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))
            self.get_toolbar('dashboard').addSeparator()

    def show_dashboard(self, show: bool = None):
        if self.dashboard is not None and self.has_action(DashBoardToolbarActions.SHOW):
            if show is None:
                show = self.is_action_checked(DashBoardToolbarActions.SHOW)
            self.dashboard.mainwindow.setVisible(show)
            self.dashboard.mainwindow.setWindowTitle('Dashboard')
            self.dashboard.mainwindow.closeEvent = lambda event: self.set_action_checked(DashBoardToolbarActions.SHOW,
                                                                                         False)
