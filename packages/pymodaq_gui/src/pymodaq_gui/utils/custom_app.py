from typing import Union, TYPE_CHECKING, Dict, Optional

import qt_themes
from qtpy.QtCore import QObject, QLocale
from qtpy import QtCore, QtWidgets

from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter import ParameterTree
from pymodaq_gui.utils.splash import get_splash_sc


class CustomApp(QObject, ActionManager, ParameterManager):
    """Base Class to ease the implementation of User Interfaces

    Inherits the MixIns ActionManager and ParameterManager classes. You have to subclass some methods and make
    concrete implementation of a given number of methods:

    * setup_actions: mandatory, see :class:`pymodaq.utils.managers.action_manager.ActionManager`
    * value_changed: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`
    * child_added: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`
    * param_deleted: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`
    * setup_docks: mandatory
    * setup_menu: non mandatory
    * connect_things: mandatory

    Attributes
    ----------
    splash_sc: QtWidgets.QSplashScreen
        A splash screen to be used to display information
    title: str
        Get/set the app title
    get_theme: method
        Returns the curretn QApplication theme, see qt_themes package

    Parameters
    ----------
    parent: DockArea or QtWidget

    See Also
    --------
    :class:`pymodaq.utils.managers.action_manager.ActionManager`,
    :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`,
    :class:`pymodaq.utils.managers.modules_manager.ModulesManager`,
    """

    log_signal = QtCore.Signal(str)
    params = []

    def __init__(self, parent: Union[DockArea, QtWidgets.QMainWindow, QtWidgets.QWidget] = None,
                 tree: ParameterTree = None, title: str = None, toolbar=None):
        QObject.__init__(self)
        ActionManager.__init__(self)
        ParameterManager.__init__(self, tree=tree)

        self._splash_sc: Optional[QtWidgets.QSplashScreen] = None

        if not (isinstance(parent, DockArea) or
                isinstance(parent, QtWidgets.QMainWindow) or
                isinstance(parent, QtWidgets.QWidget)):
            parent = QtWidgets.QWidget()

        self.parent = parent
        if isinstance(parent, DockArea):
            self.dockarea: DockArea = parent
            self.mainwindow: QtWidgets.QMainWindow = parent.parent()
        elif isinstance(parent, QtWidgets.QMainWindow):
            self.dockarea: DockArea = None
            self.mainwindow: QtWidgets.QMainWindow = parent
        else:
            self.dockarea: DockArea = None
            self.mainwindow: QtWidgets.QMainWindow = None

        self._title: str = ''
        self.title = title

        self.docks: Dict[str, Dock] = dict([])
        self.statusbar = None
        self._menubar: QtWidgets.QMenuBar = None
        if toolbar is None:
            toolbar = QtWidgets.QToolBar(self.title)
        self.set_toolbar(toolbar) # create self._toolbar

        if self.mainwindow is not None:
            self.mainwindow.setWindowTitle(self.title)
            self.mainwindow.addToolBar(self._toolbar)
            self._menubar = self.mainwindow.menuBar()
            self.statusbar = self.mainwindow.statusBar()
            self.reference_toolbar('main', self._toolbar)
        else:
            parent.setWindowTitle(self.title)

    @property
    def menubar(self):
        return self._menubar

    @property
    def splash_sc(self) -> QtWidgets.QSplashScreen:
        if not hasattr(self, "_splash_sc") or self._splash_sc is None:
            self._splash_sc = get_splash_sc()
        return self._splash_sc

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, title: str):
        self._title = title if title is not None else self.__class__.__name__
        if self.mainwindow is not None:
            self.mainwindow.setWindowTitle(self._title)

    @staticmethod
    def get_theme(name: str = None):
        return qt_themes.get_theme(name)

    def setup_ui(self):
        self.setup_docks()

        self.setup_actions()  # see ActionManager MixIn class

        try:
            self.setup_menu(self._menubar)
        except TypeError:
            self.setup_menu()  # for backcompatibility

        self.connect_things()

        self.do_things_after_ui_setup()

    def quit_fun(self):
        """Method to be subclassed in order to define a custom quit function
        """
        if self.mainwindow is not None:
            self.mainwindow.close()

    def do_things_after_ui_setup(self):
        """Non mandatory method to be subclassed in order to do things after the UI setup
        """
        pass

    def setup_docks(self):
        """Mandatory method to be subclassed to setup the docks layout

        Examples
        --------
        >>>self.docks['ADock'] = gutils.Dock('ADock name')
        >>>self.dockarea.addDock(self.docks['ADock'])
        >>>self.docks['AnotherDock'] = gutils.Dock('AnotherDock name')
        >>>self.dockarea.addDock(self.docks['AnotherDock'''], 'bottom', self.docks['ADock'])

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """
        raise NotImplementedError

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        Examples
        --------
        >>>file_menu = self._menubar.addMenu('File')
        >>>self.affect_to('load', file_menu)
        >>>self.affect_to('save', file_menu)

        >>>file_menu.addSeparator()
        >>>self.affect_to('quit', file_menu)

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        pass

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        raise NotImplementedError

