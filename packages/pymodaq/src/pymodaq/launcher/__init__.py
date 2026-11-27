from pathlib import Path

import toml

from pymodaq_utils.config import get_set_local_dir

HISTORY_FILE_NAME = 'history.toml'
HISTORY_FILE_PATH = get_set_local_dir(user=True).joinpath(HISTORY_FILE_NAME)


def load_history(path: str | Path) -> dict:
    """Read UTF-8 history or history written in the local encoding."""
    try:
        return toml.load(path)
    except UnicodeDecodeError:
        # Older versions used the system encoding when writing history.
        with open(path, encoding='locale') as stream:
            return toml.load(stream)
