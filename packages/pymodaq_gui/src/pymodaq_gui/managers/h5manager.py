
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from qtpy import QtCore, QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.utils.enums import MenuToolbarNames
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import BaseEnum, StrEnum

from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils import select_file, Dock

from pymodaq_gui.utils.widgets.multistate_led import MultistateLED
from pymodaq_gui.utils.status_palette import StatusPalette, Status
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.utils.widgets.statusbar_separator import StatuBarSeparator

logger = set_logger(get_module_name(__file__))
config = Config()


if TYPE_CHECKING:
    from pymodaq_gui.utils import CustomApp


class FileStatus(BaseEnum):
    NEW = 0
    REOPENED = 1
    CLOSED = 2
    REOPENED_ANOTHER = 3
    NO_FILE = 4


class FileAction(StrEnum):
    NEW_FILE = 'new_file'
    LOAD = 'load'
    SAVE = 'save'
    SHOW_FILE = 'show_file'
    OPEN_FILE = 'open_file'
    CLOSE_FILE = 'close_file'
    SHOW_SETTINGS = 'show_settings'


class H5Manager(QtCore.QObject, ActionManager):
    command_sig = QtCore.Signal(ThreadCommand)
    file_open_signal = QtCore.Signal(bool)
    file_loaded_signal = QtCore.Signal(Path)

    def __init__(self, app: 'CustomApp', parent=None,
                 show_not: Iterable[FileAction] = (FileAction.CLOSE_FILE, FileAction.OPEN_FILE)):
        """ Create a H5Saver manager to handle display of info in a MainWindow and expose h5 file and h5Saver
        manipulation. The CustomApp it applies to should have a mainwindow attribute pointing to a QMainWindow

        Parameters
        ----------
        app: CustomApp
            An app composed of this H5Manager
        """
        QtCore.QObject.__init__(self, parent)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        self._show_not_action = show_not

        self._h5saver: H5Saver = None
        self._app = app

        self.main_window = app.mainwindow
        self.current_folder: Path = Path(config('data', 'data_saving', 'h5file', 'save_path'))

        self._h5_base_group_name = getattr(app, 'h5_base_group_name', 'Data')

        self._file_open_LED: MultistateLED = None

        self._show_h5file_statusbar_widgets = getattr(app, '.show_h5file_statusbar_widgets', True)

        self.create_file_toolbar_and_menu()

    @property
    def statusbar(self) -> QtWidgets.QStatusBar:
        return self.main_window.statusBar()

    def settings(self) -> Parameter:
        return self.h5saver.settings

    def settings_tree(self) -> QtWidgets.QWidget:
        return self.h5saver.settings_tree

    def create_file_toolbar_and_menu(self) -> tuple[QtWidgets.QToolBar, QtWidgets.QMenu]:

        self.add_toolbar(MenuToolbarNames.FILE, 'FileActions')
        self.add_menu(MenuToolbarNames.FILE, 'FileActions')
        self.set_toolbar(MenuToolbarNames.FILE)
        self.set_menu(MenuToolbarNames.FILE)

        self.add_action(FileAction.SHOW_FILE, 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file',
                        toolbar=self.toolbar,
                        auto_toolbar=FileAction.SHOW_FILE not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.SHOW_FILE not in self._show_not_action)

        self.add_action(FileAction.NEW_FILE, 'New file', 'add_circle',
                        toolbar=self.toolbar,
                        auto_toolbar=FileAction.NEW_FILE not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.NEW_FILE not in self._show_not_action,)

        self.add_action(FileAction.LOAD, 'Open file to append...', 'file_open',
                        toolbar=self.toolbar,
                        auto_toolbar=FileAction.LOAD not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.LOAD not in self._show_not_action,)
        self.get_menu(MenuToolbarNames.FILE).addSeparator()
        self.toolbar.addSeparator()
        self.add_action(FileAction.SAVE, 'Save copy as...', 'save',
                        toolbar=self.toolbar,
                        auto_toolbar=FileAction.SAVE not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.SAVE not in self._show_not_action,)
        self.toolbar.addSeparator()
        self.get_menu(MenuToolbarNames.FILE).addSeparator()
        self.add_action(FileAction.SHOW_SETTINGS, 'Show h5 settings', 'settings',
                        toolbar=self.toolbar if FileAction.SHOW_SETTINGS not in self._show_not_action else None,
                        auto_toolbar=FileAction.SHOW_SETTINGS not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.SHOW_SETTINGS not in self._show_not_action,
                        checkable=True)

        # Debug-only actions: registered but not in any menu so they stay hidden from regular users.
        # A developer can access them programmatically or add them back to a menu as needed.
        self.add_action(FileAction.OPEN_FILE, 'Open Current File', '',
                        toolbar=self.toolbar if FileAction.OPEN_FILE not in self._show_not_action else None,
                        auto_toolbar=FileAction.OPEN_FILE not in self._show_not_action,
                        menu= self.menu,
                        auto_menu=FileAction.OPEN_FILE not in self._show_not_action
                        )
        self.add_action(FileAction.CLOSE_FILE, 'Close Current File', '',
                        toolbar=self.toolbar if FileAction.CLOSE_FILE not in self._show_not_action else None,
                        auto_toolbar=FileAction.CLOSE_FILE not in self._show_not_action,
                        menu=self.menu,
                        auto_menu=FileAction.CLOSE_FILE not in self._show_not_action
                        )


        self.connect_action(FileAction.SHOW_FILE, self.show_file_content)
        self.connect_action(FileAction.NEW_FILE, self.create_new_file)
        self.connect_action(FileAction.NEW_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.NEW_FILE)))

        self.connect_action(FileAction.LOAD, self.load_file)
        self.connect_action(FileAction.LOAD, lambda: self.command_sig.emit(ThreadCommand(FileAction.LOAD)))

        self.connect_action(FileAction.SAVE, self.save_file)
        self.connect_action(FileAction.SAVE, lambda: self.command_sig.emit(ThreadCommand(FileAction.SAVE)))

        self.connect_action(FileAction.OPEN_FILE, self.open_file)
        self.connect_action(FileAction.OPEN_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.OPEN_FILE)))

        self.connect_action(FileAction.CLOSE_FILE, self.close_file)
        self.connect_action(FileAction.CLOSE_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.CLOSE_FILE)))

        self.connect_action(FileAction.SHOW_SETTINGS, self.show_settings)
        self.connect_action(FileAction.SHOW_SETTINGS, lambda: self.command_sig.emit(ThreadCommand(FileAction.SHOW_SETTINGS)))

    def show_settings(self, show: bool = True):

        widget = self._h5saver.settings_tree
        while widget is not None:
            widget = widget.parent()
            if isinstance(widget, Dock):
                break
        if widget is None:
            widget = self._h5saver.settings_tree

        widget.setVisible(show)
        widget.closeEvent = lambda event: self.set_action_checked(FileAction.SHOW_SETTINGS, False)

    def insert_h5stuff_status(self):
        self._file_open_LED = MultistateLED(
            states=StatusPalette.subset(Status.OFF, Status.IDLE, Status.RUNNING),
            readonly=True)
        self._file_open_LED.set_state(Status.OFF)
        self._file_open_LED.setToolTip('H5 file closed')

        self.statusbar.addPermanentWidget(StatuBarSeparator())
        self.statusbar.addPermanentWidget(QtWidgets.QLabel('File:'))
        self.statusbar.addPermanentWidget(self._file_open_LED)

        self.statusbar.addPermanentWidget(StatuBarSeparator())

    def _init_h5_saver(self) -> H5Saver:
        if self._h5saver is None:
            self._h5saver = H5Saver()
            self._h5saver.settings.child('do_save').hide()
            self._h5saver.settings.child('custom_name').hide()
            self._h5saver.settings['base_name'] = self._h5_base_group_name
            self._h5saver.new_file_sig.connect(self.create_new_file)
            self._h5saver.file_changed_sig.connect(self.update_file_status_led)
        return self._h5saver

    @property
    def h5saver(self) -> H5Saver:
        self._init_h5_saver()
        if not self._h5saver.isopen():
            status = self.open_file()
            if status == FileStatus.NO_FILE:
                self.create_new_file()
        return self._h5saver

    def get_h5saver(self, create_new_file=False, mode='a') -> H5Saver:
        """ Return a H5Saver instance with more control than when using the h5saver property, in particular,
        the property will attempt to create a new file if it doesn't exist."""
        self._init_h5_saver()
        status = self.open_file(mode=mode)

        if status == FileStatus.NO_FILE and create_new_file:
            self.create_new_file()
        return self._h5saver

    def create_new_file(self):
        """ Slot of the New File button in the H5Saver settings Tree and the new file action.

        Also connected to ``new_file_sig`` (``Signal(bool)``); Qt allows a signal to connect to
        a slot taking fewer arguments than it emits, so no bool parameter is needed here.
        """
        self.close_file()
        # Explicitly create a new file (don't reopen existing)
        try:
            self._h5saver.init_file(update_h5=True)
            logger.info(f"Created new h5 file: {self._h5saver.settings['current_h5_file']}")
            self.update_file_status_led()
        except Exception as e:
            logger.error(f"Could not create new h5 file: {e}")
            QtWidgets.QMessageBox.warning(
                None, 'New File Error',
                f'Could not create a new h5 file:\n{e}',
            )

    def open_file(self, mode='a') -> FileStatus:
        """ Try to reopen the current h5 file if it is closed.
        """
        if self._h5saver is not None and not self._h5saver.isopen():
            current_file = self._h5saver.settings['current_h5_file']
            if current_file and Path(current_file).exists():
                self.current_folder = Path(current_file).parent
                return self._try_open_existing_file(current_file, mode=mode)
            else:
                return FileStatus.NO_FILE
        self.update_file_status_led()
        return FileStatus.REOPENED

    def close_file(self):
        self._h5saver.flush()
        self._h5saver.close_file()
        self.update_file_status_led()

    def flush(self):
        self.h5saver.flush()

    def _try_open_existing_file(self, current_file: str | Path, mode='a') -> FileStatus:
        """Try to open an existing file, asking user what to do if locked.

        Return:
        -------
        FileStatus
        """
        while True:
            try:
                logger.debug(f"Reopening existing h5 file: {current_file}")
                self._h5saver.init_file(addhoc_file_path=current_file,
                                        mode=mode)
                self.file_open_signal.emit(True)
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
                        self._h5saver.init_file(update_h5=True,
                                                mode=mode)
                        self.file_open_signal.emit(True)
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
                                self._h5saver.init_file(addhoc_file_path=file_path,
                                                        mode=mode)
                                self.file_open_signal.emit(True)
                                return FileStatus.REOPENED_ANOTHER
                            except Exception as e2:
                                logger.warning(f"Could not open selected file: {e2}")
                                continue  # Show dialog again
                        else:
                            continue  # User cancelled browse, show dialog again
                    else:
                        # User cancelled - leave h5_file unchanged
                        logger.info("User cancelled file selection - keeping current file state")
                        self.file_open_signal.emit(False)
                        return FileStatus.CLOSED
                else:
                    # Other error - fall back to new file
                    logger.warning(f"Could not reopen h5 file: {e}")
                    self._h5saver.init_file(update_h5=True,
                                            mode=mode)
                    self.file_open_signal.emit(True)
                    return FileStatus.NEW

    def load_file(self, mode='a'):
        file_path = select_file(self.current_folder, save=False, ext='h5')
        if not (file_path is None or file_path == ''):
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            self.current_folder = file_path.parent
            file_status = self._try_open_existing_file(file_path, mode=mode)
            self.update_file_status_led()
            if file_status not in (FileStatus.NO_FILE, FileStatus.CLOSED):
                self.file_loaded_signal.emit(file_path)

    def save_file(self):
        Path(self.h5saver.settings['base_path']).mkdir(exist_ok=True)
        filename = select_file(self.h5saver.settings['base_path'], save=True, ext='h5')
        self.h5saver.h5_file.copy_file(str(filename), overwrite=True)

    def set_file_open(self, is_open: bool):
        """Update the file-status LED's open/closed state, preserving SWMR state."""
        if self._show_h5file_statusbar_widgets and self._file_open_LED is not None:
            if not is_open:
                self._file_open_LED.set_state(Status.OFF)
                self._file_open_LED.setToolTip('H5 file closed')
            elif self._file_open_LED.get_state() == Status.OFF:
                self._file_open_LED.set_state(Status.IDLE)
                self._file_open_LED.setToolTip('H5 file open and accessible')

    def show_file_content(self):
         if self._h5saver is not None:
             self._h5saver.show_file_content()

    def set_swmr_status(self, active: bool, compatible: bool = False):
        """Reflect SWMR state on the file-status LED (only meaningful while the file is open).

        Parameters
        ----------
        active:
            True if SWMR mode is currently active on the file (shown as 'running').
        compatible:
            True if the file was created with SWMR support (informational, tooltip only).
        """
        if not self._show_h5file_statusbar_widgets or self._file_open_LED is None:
            return
        if self._file_open_LED.get_state() == Status.OFF:
            return  # file is closed, nothing to reflect
        if active:
            self._file_open_LED.set_state(Status.RUNNING)
            self._file_open_LED.setToolTip('H5 file open — SWMR mode active')
        else:
            self._file_open_LED.set_state(Status.IDLE)
            tooltip = ('H5 file open — SWMR-compatible' if compatible
                       else 'H5 file open and accessible')
            self._file_open_LED.setToolTip(tooltip)

    def update_file_status_led(self):
        """Reflect the current h5 file open/accessible and SWMR state in the status bar LED."""

        is_open = (self._h5saver is not None
                   and self._h5saver.h5_file is not None
                   and self._h5saver.isopen())
        self.set_file_open(is_open)
        swmr_active = is_open and self._h5saver.is_swmr_active
        swmr_compatible = is_open and self._h5saver.is_swmr_compatible
        self.set_swmr_status(swmr_active, swmr_compatible)
