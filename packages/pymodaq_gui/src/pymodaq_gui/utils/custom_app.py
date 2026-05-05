from pathlib import Path
from typing import Union, TYPE_CHECKING, Dict, Optional

import qt_themes
from qt_themes import Theme
from qtpy.QtCore import QObject, QLocale
from qtpy import QtCore, QtWidgets

from pymodaq_utils.config import get_set_path, get_set_local_dir
from pymodaq_utils.warnings import deprecation_msg

from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter import ParameterTree
from pymodaq_gui.utils.splash import get_splash_sc



class CustomApp(QObject, ActionManager, ParameterManager):
    """Base Class to ease the implementation of User Interfaces

    Inherits the MixIns ActionManager and ParameterManager classes. You have to subclass some methods and make
    concrete implementation of a given number of methods:

    * setup_docks_and_widgets: to code the widget layout of your Application using Docks (and the DockArea)
      or other widgets
    * setup_menus_and_toolbars: to create the menus and the toolbar associated with actions (see setup_actions)
    * setup_actions:  add actions (see :class:`pymodaq_gui.managers.action_manager.ActionManager`) or widgets and optionally add them
      to toolbar and menu
    * connect_things: to connect signals and slots. Either from actions
      (:meth:`pymodaq_gui.managers.action_manager.ActionManager.connect_action`)
      or direct signal connection

    Other methods to reimplement, related to Parameter management

    * value_changed: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`
    * child_added: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`
    * param_deleted: non mandatory, see :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`

    Depending on the object type, the mainwindow and dockarea attributes may be None

    if parent is:

    * None or QWidget, the attributes will be
        * parent = QWidget
        * maindow = None
        * dockarea = None
    * DockArea, the attributes will be
        * parent = DockArea
        * maindow = QMainWindow
        * dockarea = DockArea
    * QMainWindow, the attributes will be
        * parent = QMainWindow
        * maindow = QMainWindow
        * dockarea = None


    Attributes
    ----------
    title: str
        Get/set the app title
    parent: QWidget, QMainWindow or DockArea
    mainwindow: QMainWindow
        the parent QMainWindow
    dockarea: DockArea
        The underlying DockArea (as central widget of the QMainWindow)
    menubar: QMenuBar
        The QMainWindow menubar
    statusbar: QStatusBar
        The QMainWindow statusbar
    splash_sc: QtWidgets.QSplashScreen
        A splash screen to be used to display information
    get_theme: method
        Returns the current QApplication theme, see qt_themes package


    Parameters
    ----------
    parent: None, QWidget, QMainWindow or DockArea


    tree: ParameterTree
        an optional Custom ParameterTree
    title: str
        The title of the Application instance
    toolbar: QTtWidgets.QToolbar
        a toolbar from another parent application
    create_app_toolbar: bool
        If True (default) will create a default toolbar with the name of the application as reference and title
    add_toolbar_break: bool
        If True, will add a break in the QToolbarArea before adding the toolbar
    create_app_menu: bool
        If True (default is False) will create a default menu in the menubar with the name of the
        application as reference and title

    See Also
    --------
    :class:`pymodaq.utils.managers.action_manager.ActionManager`,
    :class:`pymodaq.utils.managers.parameter_manager.ParameterManager`,
    """

    log_signal = QtCore.Signal(str)
    params = []

    def __init__(self, parent: Union[DockArea, QtWidgets.QMainWindow, QtWidgets.QWidget] = None,
                 tree: ParameterTree = None, title: str = None, toolbar: QtWidgets.QToolBar=None,
                 create_app_toolbar: bool = True, add_toolbar_break=True,
                 create_app_menu: bool = False):

        QObject.__init__(self)
        ActionManager.__init__(self)
        ParameterManager.__init__(self, tree=tree)

        self._splash_sc: Optional[QtWidgets.QSplashScreen] = None

        if not (isinstance(parent, (DockArea, QtWidgets.QMainWindow, QtWidgets.QWidget))):
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

        self._menubar: QtWidgets.QMenuBar = None

        if toolbar is not None:
            create_app_toolbar = True  # force the app toolbar to be the given one
        if create_app_toolbar:
            self.add_toolbar(self.__class__.__name__.lower(),
                             self.__class__.__name__,
                             self.mainwindow,
                             toolbar,
                             add_break=add_toolbar_break)
            self.set_toolbar(toolbar)

        if self.mainwindow is not None:
            self.mainwindow.setWindowTitle(self.title)
            self._menubar = self.mainwindow.menuBar()
        else:
            parent.setWindowTitle(self.title)
            self._statusbar = QtWidgets.QStatusBar()

        if create_app_menu:
            self.add_menu(self.__class__.__name__.lower(),
                          self.__class__.__name__,
                          self.menubar if self.mainwindow is not None else None)

    @classmethod
    def get_local_folder(cls, user=False) -> Path:
        """ Create a local User or system wide folder to store things about this extension"""
        return get_set_path(get_set_local_dir(user=user), cls.__name__)

    @property
    def menubar(self):
        return self._menubar

    @property
    def statusbar(self) -> QtWidgets.QStatusBar | None:
        return self.mainwindow.statusBar() if self.mainwindow is not None else self._statusbar

    def update_status(self, message: str, laps_ms=500):
        self.statusbar.showMessage(message, laps_ms)

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
    def get_theme(name: str = None) -> Theme:
        return qt_themes.get_theme(name)

    def setup_ui(self):
        self.setup_docks_and_widgets()

        self.setup_menus_and_toolbars(self.menubar)  # see ActionManager MixIn class

        self.setup_actions()  # see ActionManager MixIn class

        self.connect_things()

        self.do_things_after_ui_setup()

    def quit_fun(self):
        """Method to be reimplemented in order to define a custom quit function
        """
        if self.mainwindow is not None:
            self.mainwindow.close()

    def do_things_after_ui_setup(self):
        """ Method to be reimplemented in order to do things after the UI setup
        """
        pass

    def setup_docks_and_widgets(self):
        """ Method to be reimplemented to set up the docks layout and/or widgets

        Examples
        --------
        >>>self.docks['ADock'] = gutils.Dock('ADock name')
        >>>self.dockarea.addDock(self.docks['ADock'])
        >>>self.docks['AnotherDock'] = gutils.Dock('AnotherDock name')
        >>>self.dockarea.addDock(self.docks['AnotherDock'''], 'bottom', self.docks['ADock'])

        See Also
        --------
        """
        if hasattr(self, 'setup_docks'):
            self.setup_docks()  # for backcompatibility
            deprecation_msg('You should not call setup_docks anymore, use `setup_docks_and_widgets` instead')

    def setup_docks(self):
        """ deprecated, see setup_docks_and_widgets
        """
        pass

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non-mandatory method to be subclassed in order to create menus and toolbars

        create menu and toolbar for actions defined in setup_actions, for instance:

        Examples
        --------
        >>>file_menu = self.add_menu('file_menu', 'File', self.menubar)
        >>>submenu = self.add_menu('submenu', 'ASubMenu', 'file_menu')
        >>>file_toolbar = self.add_toolbar('file_toolbar', 'File', self.mainwindow)


        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.setup_menu(menubar)  # for back-compatibility

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """ Deprecated, use `setup_menus_and_toolbars`

        """
        pass

    def setup_actions(self):
        """Method where to create actions.

        To be reimplemented

        Examples
        --------
        >>> self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True, menu='file_menu')
        >>> self.add_action('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera", checkable=False)
        >>> self.add_action('save', 'Save' 'SaveAs', "Save current data", checkable=False)

        >>>self.affect_to('load', 'file_menu')
        >>>self.affect_to('save', 'file_menu')

        """
        pass

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods

        To be reimplemented
        """
        pass

