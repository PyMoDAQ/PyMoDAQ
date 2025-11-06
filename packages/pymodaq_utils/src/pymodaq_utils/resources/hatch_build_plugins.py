from pathlib import Path
import toml

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


def update_metadata_from_toml(metadata: dict, here: Path) -> None:

    logger.debug(f'setting project metadata from: {here}')
    src_file = here.joinpath('pyproject.toml')
    src_dict = toml.load(src_file)

    PLUGIN_NAME = metadata['name']
    SHORT_PLUGIN_NAME = metadata['name'].split('pymodaq_plugins_')[1]

    metadata['urls'] = {}
    metadata['urls']['Homepage'] = "https://pymodaq.cnrs.fr"
    metadata['urls']['Documentation '] = "https://pymodaq.cnrs.fr"
    metadata['urls']['Repository '] = src_dict['urls']['package-url']

    entrypoints = {}

    if 'features' in src_dict:
        if src_dict['features'].get('instruments', False):
            entrypoints['pymodaq.instruments'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
        if src_dict['features'].get('extensions', False):
            entrypoints['pymodaq.extensions'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
        if src_dict['features'].get('pid_models', False):
            entrypoints['pymodaq.pid_models'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
        if src_dict['features'].get('models', False):
            entrypoints['pymodaq.models'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
        if src_dict['features'].get('h5exporters', False):
            entrypoints['pymodaq.h5exporters'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
        if src_dict['features'].get('scanners', False):
            entrypoints['pymodaq.scanners'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
    else:
        entrypoints['pymodaq.instruments'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}

    entrypoints['pymodaq.plugins'] = {SHORT_PLUGIN_NAME: PLUGIN_NAME}
    # generic plugin, usefull for the plugin manager
    metadata['entry-points'] = entrypoints

    logger.debug(f'created entry-points: {entrypoints}')
