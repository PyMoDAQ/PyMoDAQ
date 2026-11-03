import json
import os
import warnings
from pathlib import Path
from typing import Optional, Union

from pymodaq.utils.config import get_set_layout_path
from pymodaq.utils.gui_utils.file_io import select_file
from pymodaq.utils.safe_pickle import restricted_loads, warn_legacy_format, LegacyFormatWarning


def read_layout_file(file) -> dict:
    """Read the dockarea state stored in a layout file

    New files are json. Files written by older versions are pickles (they start with the 0x80 protocol
    byte): these are read by a restricted loader that only rebuilds plain data and never runs code.
    """
    with open(str(file), 'rb') as f:
        content = f.read()
    if content[:1] == b'\x80':
        warn_legacy_format(f'The layout file {file}')
        return restricted_loads(content)
    return json.loads(content.decode('utf-8'))


def load_layout_state(dockarea, file=None):
    """
        Load and restore a dockarea layout state from the select_file obtained pathname file.
    """
    if file is None:
        file = select_file(start_path=get_set_layout_path(), save=False, ext='dock')
    if file is not None:
        dockarea.restoreState(read_layout_file(file))
    file = file.name
    return file


def save_layout_state(dockarea, file=None):
    """
        Save the current layout state in the select_file obtained pathname file (as json).
    """

    dockstate = dockarea.saveState()
    if 'float' in dockstate:
        dockstate['float'] = []
    if file is None:
        file = select_file(start_path=get_set_layout_path(), save=True, ext='dock')
    if file is not None:
        with open(str(file), 'w', encoding='utf-8') as f:
            json.dump(dockstate, f)



def migrate_layout_file(source: Union[str, Path], destination: Optional[Union[str, Path]] = None) -> Path:
    """Write a copy of a layout file written by an older version (a pickle) as a json file

    The source file is never modified, and an existing destination file is never overwritten.

    Returns
    -------
    Path: the migrated file, by default named as the source followed by _migrated

    Raises
    ------
    FileExistsError
        if the destination exists
    UnsafePickleError
        if the file contains anything else than plain data, in this case nothing is written
    """
    source = Path(source)
    destination = source.with_name(f'{source.stem}_migrated{source.suffix}') if destination is None \
        else Path(destination)
    if destination.exists():
        raise FileExistsError(f'{destination} already exists, it will not be overwritten')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', LegacyFormatWarning)  # migrating is the answer to this warning
        state = read_layout_file(source)
    part = destination.with_name(destination.name + '.part')
    try:
        with open(part, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        os.replace(part, destination)
    finally:
        if part.exists():
            part.unlink()
    return destination
