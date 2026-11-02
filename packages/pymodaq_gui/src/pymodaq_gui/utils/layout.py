import json

from pymodaq_gui.config import get_set_layout_path
from pymodaq_gui.utils.file_io import select_file
from pymodaq_utils.safe_pickle import restricted_loads


def read_layout_file(file) -> dict:
    """Read the dockarea state stored in a layout file

    New files are json. Files written by older versions are pickles (they start with the 0x80 protocol
    byte): these are read by a restricted loader that only rebuilds plain data and never runs code.
    """
    with open(str(file), 'rb') as f:
        content = f.read()
    if content[:1] == b'\x80':
        return restricted_loads(content)
    return json.loads(content.decode('utf-8'))


def load_layout_state(dockarea, file=None, user=False):
    """
        Load and restore a dockarea layout state from the select_file obtained pathname file.
    """
    if file is None:
        file = select_file(start_path=get_set_layout_path(user=user), save=False, ext='dock')
    if file is not None:
        dockarea.restoreState(read_layout_file(file))
    file = file.name
    return file


def save_layout_state(dockarea, file=None, user=False):
    """
        Save the current layout state in the select_file obtained pathname file (as json).
    """

    dockstate = dockarea.saveState()
    if 'float' in dockstate:
        dockstate['float'] = []
    if file is None:
        file = select_file(start_path=get_set_layout_path(user=user), save=True, ext='dock')
    if file is not None:
        with open(str(file), 'w', encoding='utf-8') as f:
            json.dump(dockstate, f)
