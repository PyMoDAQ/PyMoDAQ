from importlib import import_module
from pathlib import Path

from qtpy import QtCore


from pymodaq_gui.utils import CustomApp

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import Config as ConfigUtils
from pymodaq.utils.config import Config

config_utils = ConfigUtils()
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

    def __init__(self, parent):
        super().__init__(parent)
        self.config = config

    def display_status(self, txt, wait_time=config_utils('general', 'message_status_persistence')):
        if self.statusbar is not None:
            self.statusbar.showMessage(txt, wait_time)

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
        scanner_module = import_module(f'{parent_module_name}.uis')

        scanner_path = Path(scanner_module.__path__[0])

        for file in scanner_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    uis.append(import_module(f'.{file.stem}', scanner_module.__name__))
                except (ModuleNotFoundError, Exception) as e:
                    pass
    except ModuleNotFoundError:
        pass
    finally:
        return uis
