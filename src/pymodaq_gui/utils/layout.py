import pickle

from pymodaq_utils import config as config_mod
from pymodaq_gui.utils.file_io import select_file


def load_layout_state(dockarea, file=None):
    """
        Load and restore a dockarea layout state from the select_file obtained pathname file.
    """
    if file is None:
        file = select_file(start_path=config_mod.get_set_layout_path(), save=False, ext='dock')
    if file is not None:
        with open(str(file), 'rb') as f:
            dockstate = pickle.load(f)
            dockarea.restoreState(dockstate)
    file = file.name
    return file


def save_layout_state(dockarea, file=None):
    """
        Save the current layout state in the select_file obtained pathname file.
        Once done dump the pickle.
    """

    dockstate = dockarea.saveState()
    if 'float' in dockstate:
        dockstate['float'] = []
    if file is None:
        file = select_file(start_path=config_mod.get_set_layout_path(), save=True, ext='dock')
    if file is not None:
        with open(str(file), 'wb') as f:
            pickle.dump(dockstate, f, pickle.HIGHEST_PROTOCOL)