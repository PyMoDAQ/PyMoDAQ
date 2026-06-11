from pymodaq_utils.config import get_set_local_dir

HISTORY_FILE_NAME = 'history.toml'
HISTORY_FILE_PATH = get_set_local_dir(user=True).joinpath(HISTORY_FILE_NAME)
