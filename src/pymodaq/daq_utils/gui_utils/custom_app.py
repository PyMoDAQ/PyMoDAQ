from qtpy.QtCore import QObject, QLocale
from pymodaq.daq_utils.gui_utils.dock import DockArea
from pymodaq.daq_utils.managers.action_manager import ActionManager
from pymodaq.daq_utils.managers.parameter_manager import ParameterManager
from pyqtgraph.dockarea import DockArea
from qtpy import QtCore, QtWidgets
from typing import Union


class CustomApp(QObject, ActionManager, ParameterManager):
    """Class to ease the implementation of User Interfaces

    Inherits the MixIns ActionManager and ParameterManager classes. You have to subclass some methods and make
    concrete implementation of a given number of methods:

    * setup_actions: mandatory, see ActionManager
    * value_changed: non mandatory, see ParameterManager
    * child_added: non mandatory, see ParameterManager
    * param_deleted: non mandatory, see ParameterManager
    * setup_docks: mandatory
    * setup_menu: non mandatory
    * connect_things: mandatory

    Parameters
    ----------
    parent: DockArea or QtWidget
    dashboard: DashBoard, optional

    See Also
    --------
    ActionManager, ParameterManager, ModulesManager, DashBoard

    """
    # custom signal that will be fired sometimes. Could be connected to an external object method or an internal method
    log_signal = QtCore.Signal(str)

    # list of dicts enabling the settings tree on the user interface
    params = []

    def __init__(self, parent: Union[DockArea, QtWidgets.QWidget], dashboard=None):
        QObject.__init__(self)
        ActionManager.__init__(self)
        ParameterManager.__init__(self)
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

        if not isinstance(parent, DockArea):
            if not isinstance(parent, QtWidgets.QWidget):
                raise Exception('no valid parent container, expected a DockArea or a least a QWidget')

        self.parent = parent
        if isinstance(parent, DockArea):
            self.dockarea = parent
            self.mainwindow = parent.parent()
        else:
            self.dockarea = None
            self.mainwindow = None
        self.dashboard = dashboard

        self.docks = dict([])
        self.statusbar = None
        self._toolbar = QtWidgets.QToolBar()

        if self.mainwindow is not None:
            self.mainwindow.addToolBar(self._toolbar)
            self.statusbar = self.mainwindow.statusBar()

        self.set_toolbar(self._toolbar)

    def setup_ui(self):
        self.setup_docks()

        self.setup_actions()  # see ActionManager MixIn class

        self.setup_menu()

        self.connect_things()

    def setup_docks(self):
        """
        Mandatory method to be subclassed to setup the docks layout
        for instance:

        self.docks['ADock'] = gutils.Dock('ADock name)
        self.dockarea.addDock(self.docks['ADock"])
        self.docks['AnotherDock'] = gutils.Dock('AnotherDock name)
        self.dockarea.addDock(self.docks['AnotherDock"], 'bottom', self.docks['ADock"])

        See Also
        ########
        pyqtgraph.dockarea.Dock
        """
        raise NotImplementedError

    def setup_menu(self):
        """
        Non mandatory method to be subclassed in order to create a menubar
        create menu for actions contained into the self._actions, for instance:

        For instance:

        file_menu = self._menubar.addMenu('File')
        self.affect_to('load', file_menu)
        self.affect_to('save', file_menu)

        file_menu.addSeparator()
        self.affect_to('quit', file_menu)

        See Also
        --------
        pymodaq.daq_utils.managers.action_manager.ActionManager
        """
        pass

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        raise NotImplementedError

    @property
    def modules_manager(self):
        """useful tool to interact with DAQ_Moves and DAQ_Viewers

        Will be available if a DashBoard has been set

        Returns
        -------
        ModulesManager
        """
        if self.dashboard is not None:
            return self.dashboard.modules_manager
