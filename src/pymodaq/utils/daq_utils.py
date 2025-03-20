
import importlib
from packaging import version as version_mod
import pkgutil
import platform
from pathlib import Path

from pymodaq_utils.config import Config
from pymodaq_utils.utils import get_entrypoints, ThreadCommand, getLineInfo, find_keys_from_val, is_64bits, timer  # for backcompat
from pymodaq_utils.logger import set_logger, get_module_name  # for backcompat

from pymodaq.utils.data import DataFromPlugins   # for backcompat

from pymodaq.utils.config import get_set_preset_path

if version_mod.parse(platform.python_version()) >= version_mod.parse('3.9'):
    # from version 3.9 the cache decorator is available
    from functools import cache
else:
    from functools import lru_cache as cache


logger = set_logger(get_module_name(__file__))

config = Config()


def copy_preset():                          # pragma: no cover
    path = get_set_preset_path().joinpath('preset_default.xml')
    if not path.exists():  # copy the preset_default from pymodaq folder and create one in pymodad's local folder
        with open(str(Path(__file__).parent.parent.joinpath('resources/preset_default.xml')), 'r') as file:
            path.write_text(file.read())


@cache
def get_instrument_plugins():  # pragma: no cover
    """
    Get plugins names as a list
    Parameters
    ----------
    plugin_type: (str) plugin type either 'daq_0Dviewer', 'daq_1Dviewer', 'daq_2Dviewer', 'daq_NDviewer' or 'daq_move'
    module: (module) parent module of the plugins

    Returns
    -------

    """
    plugins_import = []
    discovered_plugins = []
    discovered_plugins_all = list(get_entrypoints(group='pymodaq.plugins'))  # old naming of the instrument plugins
    discovered_plugins_all.extend(list(get_entrypoints(group='pymodaq.instruments')))  # new naming convention
    for entry in discovered_plugins_all:
        if entry.name not in [ent.name for ent in discovered_plugins]:
            discovered_plugins.append(entry)
    discovered_plugins = list(set(discovered_plugins))
    logger.debug(f'Found {len(discovered_plugins)} installed plugins, trying to import them')
    viewer_types = ['0D', '1D', '2D', 'ND']
    plugin_list = []
    for entrypoint in discovered_plugins:
        #print(f'Looking for valid instrument plugins in package: {module.value}')

        try:
            try:
                movemodule = importlib.import_module(f'{entrypoint.value}.daq_move_plugins', entrypoint.value)
                plugin_list.extend([{'name': mod[len('daq_move') + 1:],
                                     'module': movemodule,
                                     'parent_module': importlib.import_module(entrypoint.value),
                                     'type': 'daq_move'}
                                    for mod in [mod[1] for mod in pkgutil.iter_modules([str(movemodule.path.parent)])]
                                    if 'daq_move' in mod])
                if len(plugin_list) > 0:
                    logger.debug(f"Found Move Instrument:"
                                f" {plugin_list[-1]['module'].__name__}/{plugin_list[-1]['name']}")
            except ModuleNotFoundError:
                pass

            viewer_modules = {}
            for vtype in viewer_types:
                try:
                    viewer_modules[vtype] = importlib.import_module(f'{entrypoint.value}.daq_viewer_plugins.plugins_{vtype}',
                                                    entrypoint.value)
                    plugin_list.extend([{'name': mod[len(f'daq_{vtype}viewer') + 1:],
                                     'module': viewer_modules[vtype],
                                     'parent_module': importlib.import_module(entrypoint.value),
                                     'type': f'daq_{vtype}viewer'}
                                    for mod in [mod[1] for mod in pkgutil.iter_modules([str(viewer_modules[vtype].path.parent)])]
                                    if f'daq_{vtype}viewer' in mod])
                    if len(plugin_list) > 0:
                        logger.debug(f"Found Viewer Instrument: "
                                    f"{plugin_list[-1]['module'].__name__}/{plugin_list[-1]['name']}")
                except ModuleNotFoundError:
                    pass

        except Exception as e:  # pragma: no cover
            logger.debug(str(e))

    for mod in plugin_list:
        try:
            plugin_type = mod['type']
            if plugin_type == 'daq_move':
                submodule = mod['module']
                importlib.import_module(f'{submodule.__package__}.daq_move_{mod["name"]}')
            else:
                submodule = mod['module']
                importlib.import_module(f'{submodule.__package__}.daq_{plugin_type[4:6]}viewer_{mod["name"]}')
            plugins_import.append(mod)
            logger.info(f"{mod['module'].__name__}/{mod['name']} available")
        except Exception as e:  # pragma: no cover
            """If an error is generated at the import, then exclude this plugin"""
            logger.debug(f'Impossible to import Instrument plugin {mod["name"]}'
                         f' from module: {mod["parent_module"].__package__}')


    # add utility plugin for PID
    try:
        pidmodule = importlib.import_module('pymodaq.extensions.pid')
        mod = [{'name': 'PID',
               'module': pidmodule,
               'parent_module': pidmodule,
               'type': 'daq_move'}]
        importlib.import_module(f'{pidmodule.__package__}.daq_move_PID')
        plugins_import.extend(mod)

    except Exception as e:
        logger.debug(f'Impossible to import PID utility plugin: {str(e)}')

    plugins_import.sort(key=lambda mod: mod['name'])
    return plugins_import


def get_plugins(plugin_type='daq_0Dviewer'):  # pragma: no cover
    """
    Get plugins names as a list
    Parameters
    ----------
    plugin_type: (str) plugin type either 'daq_0Dviewer', 'daq_1Dviewer', 'daq_2Dviewer', 'daq_NDviewer' or 'daq_move'
    module: (module) parent module of the plugins

    Returns
    -------

    """
    return [plug for plug in get_instrument_plugins() if plug['type'] == plugin_type]

