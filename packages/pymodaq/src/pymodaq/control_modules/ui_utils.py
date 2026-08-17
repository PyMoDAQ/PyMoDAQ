from importlib import import_module
from pathlib import Path
from typing import Union
import numpy as np
from qtpy import QtCore, QtWidgets
import qt_themes

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils import Dock
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_gui.utils.styling import create_font, create_icon
from pymodaq_gui.plotting.utils.plot_utils import display_in_dock
from pymodaq_gui.utils.widgets.widget_with_label_title import WidgetWithLabelTitle
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import GlobalConfig as Config

config = Config()


class ControlModuleUI(CustomApp):
    """ Base Class for ControlModules UIs

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
        See specific implementation

    See Also
    --------
    :class:`daq_move_ui.DAQ_Move_UI`, :class:`daq_viewer_ui.DAQ_Viewer_UI`
    """
    command_sig = QtCore.Signal(ThreadCommand)

    # Common icon name for initialization action
    INIT_ICON = 'cable'

    def __init__(self, parent, title, settings_dock: Dock = None,):
        super().__init__(parent, title=title)
        self.settings_dock: Dock = settings_dock
        self.config = config
        self._ini_state = False

        self._settings_widget = WidgetWithLabelTitle(self.title)
        self._settings_widget.setLayout(QtWidgets.QVBoxLayout())

    def add_setting_tree(self, tree):
        self._settings_widget.insert_widget(tree)

    # ---- Common action setup methods ----

    def _setup_name_widget(self, toolbar: QtWidgets.QToolBar = None) -> None:
        """Add the module name label to the toolbar

        Parameters
        ----------
        toolbar: QToolBar
            The toolbar to add the widget to. If None, uses default toolbar.

        """
        self.add_widget('name', LabelWithFont(f'{self.title}', font_name="Tahoma",
                                                font_size=14, isbold=True, isitalic=True),
                        toolbar=toolbar)

    def _setup_init_action(self, toolbar: QtWidgets.QToolBar = None,
                           action_name: str = 'init',
                           display_name: str = 'Initialize',
                           tip: str = 'Connect to selected module') -> None:
        """Add the initialization action to the toolbar

        Parameters
        ----------
        toolbar: QToolBar
            The toolbar to add the action to. If None, uses default toolbar.
        action_name: str
            The internal name for the action (e.g., 'ini_actuator', 'ini_detector')
        display_name: str
            The display name for the action
        tip: str
            Tooltip text
        """
        self._init_action_name = action_name
        self.add_action(action_name, display_name, self.INIT_ICON, checkable=True,
                        tip=tip, icon_color=self.get_theme().red,
                        icon_checked_color=self.get_theme().green,
                        toolbar=toolbar)

    def _setup_settings_action(self, toolbar: QtWidgets.QToolBar = None) -> None:
        """Add the show settings action to the toolbar

        Parameters
        ----------
        toolbar: QToolBar
            The toolbar to add the action to. If None, uses default toolbar.
        """
        self.add_action('show_settings', 'Show Settings', 'settings', "Show Settings",
                        checkable=True, icon_checked_color=self.get_theme().green,
                        toolbar=toolbar)

    def update_init_icon(self, initialized: bool, action_name: str = 'init') -> None:
        """Update the initialization action icon based on state

        Parameters
        ----------
        initialized: bool
            Whether the module is initialized
        action_name: str
            The name of the init action
        """
        if self.has_action(action_name):
            self.get_action(action_name).set_icon(self.INIT_ICON, self.get_theme().green if
            initialized else self.get_theme().red)

    def enable_actions(self, status=True, all_except=()):
        """Enable or disable all toolbar actions, optionally excluding some.

        Parameters
        ----------
        status: bool
            True to enable, False to disable.
        all_except: tuple of str
            Action names to leave unchanged.
        """
        for action in self.actions_names:
            if action not in all_except:
                self.set_action_enabled(action, status)

    def _show_settings(self, show: bool = True):
        """Slot connected to the show_settings action."""
        if (self.config('pymodaq', 'control_modules', 'settings_as_popup')
            or self.settings_dock is None):
            if self.settings_dock is not None:
                self.settings_dock.removeWidgets(close=False)
                self.settings_dock.setVisible(False)

            self._settings_widget.setWindowTitle(f'{self.title} settings')
            self._settings_widget.setVisible(show)
            self._settings_widget.closeEvent = lambda event: self.set_action_checked('show_settings', False)
        else:
            display_in_dock(show,
                            self._settings_widget,
                            self.settings_dock)

    def show_settings(self, show=True):
        """Programmatically show/hide the settings widget. API entry."""
        if self.is_action_checked('show_settings') != show:
            self.get_action('show_settings').trigger()

    def _connect_common_actions(self):
        """Connect actions that are common to all control module UIs.

        Connects `show_settings` → `_show_settings` and the init action → `send_init`.
        Subclasses should call this at the start of their `connect_things()`.
        """
        if 'show_settings' in self.actions_names:
            self.connect_action('show_settings', self._show_settings)
        if hasattr(self, '_init_action_name') and self._init_action_name in self.actions_names:
            self.connect_action(self._init_action_name, self.send_init)

    def close(self):
        """Close and clean up the settings widget. Subclasses should call super().close()."""
        if self._settings_widget is not None:
            self._settings_widget.close()

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        raise NotImplementedError

    def send_init(self, checked: bool):
        """Should be implemented to send to the main app the fact that someone (un)checked init."""
        raise NotImplementedError


def register_uis(parent_module_name: str = 'pymodaq.control_modules.daq_move_ui'):
    uis = []
    try:
        module = import_module(f'{parent_module_name}.uis')

        path = Path(module.__path__[0])

        for file in path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    uis.append(import_module(f'.{file.stem}', module.__name__))
                except (ModuleNotFoundError, Exception) as e:
                    pass
    except ModuleNotFoundError:
        pass
    finally:
        return uis
