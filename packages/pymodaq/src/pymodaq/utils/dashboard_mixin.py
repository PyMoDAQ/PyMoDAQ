"""Everything an object needs to work with a DashBoard.

Shared by the extensions (:class:`~pymodaq.utils.custom_ext.CustomExt`) and by the managers needing
the dashboard (``ROIManager``, ``ExperimentManager``, ``StateManager``...).
It lives in ``pymodaq`` because the lower packages (``pymodaq_gui``...) must not import it.
"""
from typing import Any, Optional, Type, TYPE_CHECKING

from pymodaq_utils.enums import StrEnum

from pymodaq.utils.managers.modules.modules_manager import ModulesManager

if TYPE_CHECKING:
    from pymodaq_gui.utils.custom_app import CustomApp
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
    from pymodaq.utils.managers.state.state_manager import StateManager

    # the mixin uses the toolbar, action and theme methods of the CustomApp it is combined with
    _MixinBase = CustomApp
else:
    _MixinBase = object


class DashBoardToolbarActions(StrEnum):
    """Names of the actions of the toolbar created by :meth:`DashboardMixin.create_dashboard_toolbar`"""
    LABEL = 'label'
    SHOW = 'show_dashboard'


class DashboardMixin(_MixinBase):
    """ Gives access to the dashboard and to a ModulesManager built on its control modules

    To be placed *before* a :class:`~pymodaq_gui.utils.custom_app.CustomApp` (or subclass) in the
    bases, for instance ``class MyExt(DashboardMixin, CustomApp)``. It has no ``__init__`` on purpose:
    the Qt side of the object (``QObject.__init__``...) must be initialized first. The class using it
    calls :meth:`init_dashboard` then :meth:`connect_experiment_manager` once that is done:

    * :class:`~pymodaq.utils.custom_ext.CustomExt` right after ``CustomApp.__init__``, the call for an experiment
      already applied being made at the end of its ``setup_ui``
    * the managers through the hooks of :class:`~pymodaq_gui.managers.manager_base.ManagerBase`
      (:meth:`init_extra` before the UI is set up, :meth:`finish_init` once the manager is built)
    """

    dashboard: Optional['DashBoard'] = None
    own_modules_manager = True  # False: use the modules manager of the dashboard instead of a copy of its modules
    _modules_manager: ModulesManager = None  # type: ignore[assignment]  # None without a dashboard

    @property
    def is_dashboard_available(self) -> bool:
        """ Whether a dashboard has been given """
        return self.dashboard is not None

    def init_dashboard(self, dashboard: Optional['DashBoard'] = None,
                       module_manager_class: Type[ModulesManager] = ModulesManager) -> None:
        """ Set the dashboard and create the modules manager from its control modules

        Parameters
        ----------
        dashboard: DashBoard, optional
            The dashboard to work with. Without it, there is no modules manager nor experiment manager
        module_manager_class: type
            The class of the modules manager to create (ModulesManager or a subclass)
        """
        self.dashboard = dashboard

        if dashboard is not None and self.own_modules_manager:
            self._modules_manager = module_manager_class(
                detectors=dashboard.detector_modules,
                actuators=dashboard.actuators_modules,
                parent_name=self.__class__.__name__)
        else:
            self._modules_manager = None  # type: ignore[assignment]

    def connect_experiment_manager(self, apply_now: bool = True) -> None:
        """ Call do_things_after_experiment_set each time an experiment is applied

        Parameters
        ----------
        apply_now: bool
            If True, also call it now if an experiment is already applied. CustomExt passes False and makes this call
            at the end of its setup_ui instead (see :meth:`apply_current_experiment`): the hook may need the UI.
        """
        if self.dashboard is not None and self.experiment_manager is not None:
            self.experiment_manager.applied_entry.connect(self.do_things_after_experiment_set)
            if apply_now:
                self.apply_current_experiment()

    def apply_current_experiment(self, show_dashboard: Optional[bool] = None) -> None:
        """ Call do_things_after_experiment_set if an experiment is already applied in the dashboard"""
        if (self.dashboard is not None and self.experiment_manager is not None
                and self.experiment_manager.entry_applied):
            self.do_things_after_experiment_set(self.experiment_manager.entry, show_dashboard)

    # hooks of ManagerBase
    def init_extra(self, dashboard: Optional['DashBoard'] = None,
                   module_manager_class: Type[ModulesManager] = ModulesManager) -> None:
        """Hook called by ManagerBase before the UI is set up: see :meth:`init_dashboard`"""
        self.init_dashboard(dashboard, module_manager_class)

    def finish_init(self) -> None:
        """Hook called by ManagerBase once the manager is built: see :meth:`connect_experiment_manager`"""
        self.connect_experiment_manager()

    @property
    def experiment_manager(self) -> Optional['ExperimentManager']:
        """The experiment manager of the dashboard, None if there is no dashboard"""
        if self.dashboard is not None:
            return self.dashboard.experiment_manager
        return None

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: Optional[bool] = None) -> None:
        """ This method is called whenever an experiment entry has been set.

        Its main purpose is to update the list of control modules in the manager and
        some other actions.

        Can be reimplemented to add some more evolved actions

        Parameters
        ----------
        experiment_name: str
            The name of the experiment entry that has been set
        show_dashboard: bool, optional
            Show (True) or hide (False) the dashboard. If None, the state of the dashboard toolbar action is used
        """
        # update modules manager
        if self.dashboard is not None:
            if self.own_modules_manager:
                self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all
                self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all

            # show/hide dashboard
            self.show_dashboard(show_dashboard)

    @property
    def state_manager(self) -> Optional['StateManager']:
        """The state manager of the dashboard, None if there is no dashboard"""
        if self.dashboard is not None:
            return self.dashboard.state_manager
        return None

    @property
    def splash(self) -> Any:
        """The splash screen of the dashboard, None if there is no dashboard"""
        if self.dashboard is not None:
            return self.dashboard.splash_sc
        return None

    @property
    def modules_manager(self) -> ModulesManager:
        """useful tool to interact with DAQ_Moves and DAQ_Viewers

        Will be available if a DashBoard has been set. It is either a ModulesManager of its own, filled with the
        control modules of the dashboard when an experiment is applied (its selection of modules is then independent
        of the others), or the one of the dashboard itself if ``own_modules_manager`` is False, always up to date.

        Returns
        -------
        ModulesManager
            None if no dashboard has been set
        """
        if not self.own_modules_manager:
            return self.dashboard.modules_manager if self.dashboard is not None else None  # type: ignore[return-value]
        return self._modules_manager

    def create_dashboard_toolbar(self,
                                 add_dashboard: bool = True,
                                 add_experiment: bool = True,
                                 add_state: bool = True,
                                 add_break: bool = True) -> None:
        """ Creates and add a toolbar named dashboard containing means to show/hide the dashboard and optionally
        to display the experiment and state manager in this toolbar

        A dashboard must have been set if add_experiment or add_state is True.
        """

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
            self.experiment_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))  # type: ignore[union-attr]  # needs a dashboard
            self.get_toolbar('dashboard').addSeparator()
        if add_state:
            self.state_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('dashboard'))  # type: ignore[union-attr]  # needs a dashboard
            self.get_toolbar('dashboard').addSeparator()

    def show_dashboard(self, show: Optional[bool] = None) -> None:
        """Show or hide the dashboard window (needs the dashboard toolbar action, see create_dashboard_toolbar)

        Parameters
        ----------
        show: bool, optional
            If None, the state of the toolbar action is used
        """
        if self.dashboard is not None and self.has_action(DashBoardToolbarActions.SHOW):
            if show is None:
                show = self.is_action_checked(DashBoardToolbarActions.SHOW)
            self.dashboard.mainwindow.setVisible(show)
            self.dashboard.mainwindow.setWindowTitle('Dashboard')
            self.dashboard.mainwindow.closeEvent = lambda event: self.set_action_checked(DashBoardToolbarActions.SHOW,
                                                                                         False)
