
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.utils.enums import MenuToolbarNames
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import BaseEnum, StrEnum

from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils import select_file

from pymodaq_gui.utils.widgets import QLED
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


class H5Manager(QtCore.QObject, ActionManager):
    command_sig = QtCore.Signal(ThreadCommand)

    def __init__(self, app: 'CustomApp', parent=None):
        """ Create a H5Saver manager to handle display of info in a MainWindow and expose h5 file and h5Saver
        manipulation. The CustomApp it applies to should have a mainwindow attribute pointing to a QMainWindow

        Parameters
        ----------
        app: CustomApp
            An app composed of this H5Manager
        """
        QtCore.QObject.__init__(self, parent)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())

        self._h5saver: H5Saver = None  #  call self.h5saver property
        self._app = app

        self.main_window = app.mainwindow

        self._h5_base_group_name = getattr(app, 'h5_base_group_name', 'Data')

        self._file_open_LED: QLED = None
        self._swmr_label: QtWidgets.QLabel = None

        self._show_h5file_statusbar_widgets = getattr(app, '.show_h5file_statusbar_widgets', True)

        self.create_file_toolbar_and_menu()

    @property
    def statusbar(self) -> QtWidgets.QStatusBar:
        return self.main_window.statusBar()

    def create_file_toolbar_and_menu(self) -> tuple[QtWidgets.QToolBar, QtWidgets.QMenu]:

        self.add_toolbar(MenuToolbarNames.FILE, 'FileActions')
        self.add_menu(MenuToolbarNames.FILE, 'FileActions')
        self.set_toolbar(MenuToolbarNames.FILE)
        self.set_menu(MenuToolbarNames.FILE)

        self.add_action(FileAction.SHOW_FILE, 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file',
                        toolbar=self.toolbar,
                        menu=self.menu)

        self.add_action(FileAction.NEW_FILE, 'New file', 'add_circle',
                        toolbar=self.toolbar,
                        menu=self.menu,)

        self.add_action(FileAction.LOAD, 'Open file to append...', 'file_open',
                        toolbar=self.toolbar,
                        menu=self.menu,)
        self.get_menu(MenuToolbarNames.FILE).addSeparator()
        self.add_action(FileAction.SAVE, 'Save copy as...', 'save',
                        toolbar=self.toolbar,
                        menu=self.menu,)

        # Debug-only actions: registered but not in any menu so they stay hidden from regular users.
        # A developer can access them programmatically or add them back to a menu as needed.
        self.add_action(FileAction.OPEN_FILE, 'Open current file', '', auto_toolbar=False, auto_menu=False)
        self.add_action(FileAction.CLOSE_FILE, 'Close current file', '', auto_toolbar=False, auto_menu=False)


        self.connect_action(FileAction.SHOW_FILE, self.show_file_content)
        self.connect_action(FileAction.NEW_FILE, lambda: self.create_new_file(True))
        self.connect_action(FileAction.NEW_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.NEW_FILE)))

        self.connect_action(FileAction.LOAD, self.load_file)
        self.connect_action(FileAction.LOAD, lambda: self.command_sig.emit(ThreadCommand(FileAction.LOAD)))

        self.connect_action(FileAction.SAVE, self.save_file)
        self.connect_action(FileAction.SAVE, lambda: self.command_sig.emit(ThreadCommand(FileAction.SAVE)))

        self.connect_action(FileAction.OPEN_FILE, self.open_file)
        self.connect_action(FileAction.OPEN_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.OPEN_FILE)))

        self.connect_action(FileAction.CLOSE_FILE, self.close_file)
        self.connect_action(FileAction.CLOSE_FILE, lambda: self.command_sig.emit(ThreadCommand(FileAction.CLOSE_FILE)))


    def insert_h5stuff_status(self):
        self._file_open_LED = QLED()
        self._file_open_LED.set_as_false()
        self._file_open_LED.clickable = False
        self._file_open_LED.setToolTip('H5 file open and accessible')

        self._swmr_label = QtWidgets.QLabel('')
        self._swmr_label.setToolTip('SWMR mode status')
        self._swmr_label.setVisible(False)
        self.statusbar.addPermanentWidget(StatuBarSeparator())
        self.statusbar.addPermanentWidget(QtWidgets.QLabel('File:'))
        self.statusbar.addPermanentWidget(self._file_open_LED)
        self.statusbar.addPermanentWidget(self._swmr_label)

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

        status = self.open_file()
        if status == FileStatus.NO_FILE:
            self.create_new_file(True)
        return self._h5saver

    def get_h5saver(self, create_new_file=False) -> H5Saver:
        """ Return a H5Saver instance with more control than when using the h5saver property, in particular,
        the property will attempt to create a new file if it doesn't exist."""
        self._init_h5_saver()
        status = self.open_file()

        if status == FileStatus.NO_FILE and create_new_file:
            self.create_new_file(True)
        return self._h5saver

    @QtCore.Slot(bool)
    def create_new_file(self, new_file):
        """ Slot of the New File button in the H5Saver settings Tree and the new file action"""

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
        self.update_file_status_led()
        return FileStatus.REOPENED

    def close_file(self):
        self._h5saver.close_file()
        self.update_file_status_led()

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
        if self._show_h5file_statusbar_widgets and self._file_open_LED is not None:
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
        if self._show_h5file_statusbar_widgets and self._swmr_label is not None:
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