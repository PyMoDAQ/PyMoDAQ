from pathlib import Path
from typing import Union, TYPE_CHECKING, Dict, Optional

import qt_themes
from qt_themes import Theme
from qtpy.QtCore import QObject, QLocale
from qtpy import QtCore, QtWidgets

from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import get_set_path, get_set_local_dir
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_utils.enums import BaseEnum
from pymodaq_gui.utils.widgets import QLED
from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter import ParameterTree
from pymodaq_gui.utils.splash import get_splash_sc
from pymodaq_gui.utils import select_file

from pymodaq_gui.h5modules.saving import H5Saver

logger = set_logger(get_module_name(__file__))
config = Config()


class FileStatus(BaseEnum):
    NEW = 0
    REOPENED = 1
    CLOSED = 2
    REOPENED_ANOTHER = 3
    NO_FILE = 4


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
    _show_h5file_widgets = False
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

        self.runner_thread: QtCore.QThread = None

        self._title: str = ''
        self.title = title
        self._h5saver: H5Saver = None  # to use only if you want to save data,
        # then call self.h5saver property
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

    def populate_status_bar(self):
        """Generic method to populate the Status Bar

        for customization, reimplement insert_custom_status_widgets method
        """
        self._status_message_label = QtWidgets.QLabel('')
        self.statusbar.addPermanentWidget(self._status_message_label)

        self.insert_custom_status_widgets()

        if self._show_h5file_widgets:
            self.insert_h5stuff_status()

    def set_permanent_status(self, status: str):
        """ Display a permanent status message

        Method populate_status_bar should have been called beforehand

        """
        self._status_message_label.setText(status)

    def insert_custom_status_widgets(self):
        """ create here Widgets to be added to the StatusBar
        To be reimplemented

        Examples
        --------
        self._file_open_LED = QLED()
        self.statusbar.addPermanentWidget(self._file_open_LED)
        """
        pass

    def update_status(self, message: str, wait_time: Optional[int] = None):
        """Show the message in the status bar with a delay of wait_time ms.
        """
        if self.statusbar is not None:
            if wait_time is None:
                wait_time = config('gui', 'message_status_persistence')
            self.statusbar.showMessage(message, wait_time)

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
        if self.runner_thread is not None:
            self.exit_runner_thread()
        if self.mainwindow is not None:
            self.mainwindow.close()

    def exit_runner_thread(self, duration : int = 5000):
        self.runner_thread.quit()
        terminated = self.runner_thread.wait(duration)
        if not terminated:
            self.runner_thread.terminate()
            self.runner_thread.wait()

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

    def insert_h5stuff_status(self):
        self._file_open_LED = QLED()
        self._file_open_LED.set_as_false()
        self._file_open_LED.clickable = False
        self._file_open_LED.setToolTip('H5 file open and accessible')

        self._swmr_label = QtWidgets.QLabel('')
        self._swmr_label.setToolTip('SWMR mode status')
        self._swmr_label.setVisible(False)

        self.statusbar.addPermanentWidget(QtWidgets.QLabel('File:'))
        self.statusbar.addPermanentWidget(self._file_open_LED)
        self.statusbar.addPermanentWidget(self._swmr_label)

    @property
    def h5saver(self) -> H5Saver:
        if self._h5saver is None:
            self._h5saver = H5Saver()
            self._h5saver.settings.child('do_save').hide()
            self._h5saver.settings.child('custom_name').hide()
            self._h5saver.settings['base_name'] = self._h5_base_group_name
            self._h5saver.new_file_sig.connect(self.create_new_file)
            self._h5saver.file_changed_sig.connect(self.update_file_status_led)

        status = self.open_file()
        if status == FileStatus.NO_FILE:
            self.create_new_file(True)
        return self._h5saver

    @QtCore.Slot(bool)
    def create_new_file(self, new_file):
        """ Slot of the New File button in the H5Saver settings Tree"""

        if new_file:
            self.close_file()
            # Explicitly create a new file (don't reopen existing)
            try:
                self._h5saver.init_file(update_h5=True)
                logger.info(f"Created new h5 file: {self._h5saver.settings['current_h5_file']}")
            except Exception as e:
                logger.error(f"Could not create new h5 file: {e}")

    def open_file(self) -> FileStatus:
        """ Try to reopen the current h5 file if it is closed.
        """
        if self._h5saver is not None and not self._h5saver.isopen():
            current_file = self._h5saver.settings['current_h5_file']
            if current_file and Path(current_file).exists():
                return self._try_open_existing_file(current_file)
            else:
                return FileStatus.NO_FILE
        return FileStatus.REOPENED

    def close_file(self):
        self._h5saver.close_file()

    def _try_open_existing_file(self, current_file: str | Path) -> FileStatus:
        """Try to open an existing file, asking user what to do if locked.

        Return:
        -------
        FileStatus
        """
        while True:
            try:
                logger.debug(f"Reopening existing h5 file: {current_file}")
                self._h5saver.init_file(addhoc_file_path=current_file)
                return FileStatus.REOPENED  # Success
            except Exception as e:
                if 'lock' in str(e).lower() or 'errno = 0' in str(e).lower():
                    # File is locked - ask user what to do
                    msg = QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                    msg.setWindowTitle("File Locked")
                    msg.setText(f"Cannot open file:\n{current_file}\n\n"
                                f"The file may be open in another application.")
                    msg.setInformativeText("Close the file elsewhere and click Retry, "
                                           "or select a different file.")
                    retry_btn = msg.addButton("Retry", QtWidgets.QMessageBox.ButtonRole.ActionRole)
                    new_auto_btn = msg.addButton("New File (Auto)", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                    browse_btn = msg.addButton("Browse...", QtWidgets.QMessageBox.ButtonRole.ActionRole)
                    msg.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
                    msg.exec()

                    if msg.clickedButton() == retry_btn:
                        continue  # Try again
                    elif msg.clickedButton() == new_auto_btn:
                        logger.info("User chose to create new file (auto)")
                        self._h5saver.init_file(update_h5=True)
                        return FileStatus.NEW
                    elif msg.clickedButton() == browse_btn:
                        # Let user select an existing file to append to
                        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                            None, "Select HDF5 File",
                            str(Path(current_file).parent),
                            "HDF5 Files (*.h5);;All Files (*)",
                        )
                        if file_path:
                            logger.info(f"User selected file: {file_path}")
                            try:
                                self._h5saver.init_file(addhoc_file_path=file_path)
                                return FileStatus.REOPENED_ANOTHER
                            except Exception as e2:
                                logger.warning(f"Could not open selected file: {e2}")
                                continue  # Show dialog again
                        else:
                            continue  # User cancelled browse, show dialog again
                    else:
                        # User cancelled - leave h5_file unchanged
                        logger.info("User cancelled file selection - keeping current file state")
                        return FileStatus.CLOSED
                else:
                    # Other error - fall back to new file
                    logger.warning(f"Could not reopen h5 file: {e}")
                    self._h5saver.init_file(update_h5=True)
                    return FileStatus.NEW

    def load_file(self):
        self.h5saver.load_file(self.h5saver.h5_file_path)
        self.update_file_status_led()

    def save_file(self):
        Path(self.h5saver.settings['base_path']).mkdir(exist_ok=True)
        filename = select_file(self.h5saver.settings['base_path'], save=True, ext='h5')
        self.h5saver.h5_file.copy_file(str(filename), overwrite=True)

    def set_file_open(self, is_open: bool):
        """Update the file-open status LED.

        Parameters
        ----------
        is_open:
            True (green) if the h5 file is open and accessible, False (red) otherwise.
        """
        if self._show_h5file_widgets:
            self._file_open_LED.set_as(is_open)

    def show_file_content(self):
         if self._h5saver is not None:
             self._h5saver.show_file_content()

    def set_swmr_status(self, active: bool, compatible: bool = False):
        """Show or hide the SWMR mode indicator in the status bar.

        Parameters
        ----------
        active:
            True if SWMR mode is currently active on the file.
        compatible:
            True if the file was created with SWMR support.
        """
        if self._show_h5file_widgets:
            if active:
                self._swmr_label.setText('SWMR')
                self._swmr_label.setToolTip('SWMR mode active')
                self._swmr_label.setVisible(True)
            elif compatible:
                self._swmr_label.setText('SWMR file')
                self._swmr_label.setToolTip('File created with SWMR support')
                self._swmr_label.setVisible(True)
            else:
                self._swmr_label.setText('')
                self._swmr_label.setToolTip('SWMR mode status')
                self._swmr_label.setVisible(False)

    def update_file_status_led(self):
        """Reflect the current h5 file open/accessible state in the status bar LED
        and the SWMR mode indicator."""

        is_open = (self._h5saver is not None
                   and self._h5saver.h5_file is not None
                   and self._h5saver.isopen())
        self.set_file_open(is_open)
        swmr_active = is_open and self._h5saver.is_swmr_active
        swmr_compatible = is_open and self._h5saver.is_swmr_compatible
        self.set_swmr_status(swmr_active, swmr_compatible)
