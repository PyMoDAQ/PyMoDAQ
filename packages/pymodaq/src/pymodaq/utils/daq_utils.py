
import importlib
import inspect
from packaging import version as version_mod
import pkgutil
import platform
from pathlib import Path

from pymodaq_utils.utils import get_entrypoints, ThreadCommand, getLineInfo, find_keys_from_val, is_64bits, timer  # for backcompat
from pymodaq_utils.logger import set_logger, get_module_name  # for backcompat
from pymodaq_utils.config import GlobalConfig
from pymodaq.utils.data import DataFromPlugins   # for backcompat

from pymodaq.utils.config import get_set_experiment_path

if version_mod.parse(platform.python_version()) >= version_mod.parse('3.9'):
    # from version 3.9 the cache decorator is available
    from functools import cache
else:
    from functools import lru_cache as cache


logger = set_logger(get_module_name(__file__))



def copy_experiment():                          # pragma: no cover
    path = get_set_experiment_path().joinpath('default.xml')
    if not path.exists():  # copy the experiment_default from pymodaq folder and create one in pymodaq's local folder
        with open(str(Path(__file__).parent.parent.joinpath('resources/experiment_default.xml')), 'r') as file:
            path.write_text(file.read())


# entry point groups declared by plugin packages (see pymodaq_utils.resources.hatch_build_plugins)
PLUGIN_ENTRYPOINT_GROUPS = ('pymodaq.plugins', 'pymodaq.instruments', 'pymodaq.extensions', 'pymodaq.models',
                            'pymodaq.pid_models', 'pymodaq.h5exporters', 'pymodaq.scanners')


def get_plugin_packages() -> list[str]:
    """ Get the names of the installed plugin packages, from their entry points (any PyMoDAQ group)"""
    packages = []
    for group in PLUGIN_ENTRYPOINT_GROUPS:
        for entrypoint in get_entrypoints(group=group):
            package = entrypoint.value.split(':')[0]
            if package not in packages:
                packages.append(package)
    return packages


@cache
def register_plugin_configs() -> list[str]:
    """ Register in GlobalConfig the ``Config`` class of the ``utils`` module of each installed plugin package

    Called when PyMoDAQ is imported, whatever the plugin contains (instruments, extensions, models...), so that
    ``GlobalConfig()(short_name, ...)`` works everywhere. A package whose ``utils`` module cannot be imported or
    defines no ``Config`` is skipped with a warning. Called once (cached).

    Returns
    -------
    list of str: the names under which the configs have been registered by this call
    """
    config = GlobalConfig()
    registered = []
    for package in get_plugin_packages():
        try:
            plugin_utils = importlib.import_module(f'{package}.utils')
        except Exception as e:
            logger.warning(f'Impossible to import {package}.utils, its configuration is not registered: {str(e)}')
            continue
        config_class = getattr(plugin_utils, 'Config', None)
        if config_class is None:
            logger.warning(f'{package}.utils defines no Config class, no configuration registered')
            continue
        name = config_class.config_name
        if isinstance(name, str) and 'config_' in name:  # same naming as GlobalConfig.register
            name = name.split('config_')[-1]
        if name in config:
            if not isinstance(config[name], config_class):  # else registered already by its decorator
                logger.warning(f'The configuration of {package} is not registered: another one is registered '
                               f'under the same name: {name}')
            continue
        try:
            GlobalConfig.register()(config_class)
            registered.append(name)
        except Exception as e:
            logger.warning(f'Impossible to register the configuration of {package}: {str(e)}')
    return registered


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
    register_plugin_configs()  # already done when importing pymodaq, plugin modules may need their config
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
                         f' from module: {mod["parent_module"].__package__} \n {str(e)}')


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

    # add utility plugin for DataMixer
    try:
        data_mixer_module = importlib.import_module('pymodaq.extensions.data_mixer')
        mod = [{'name': 'DataMixer',
                'module': data_mixer_module,
                'parent_module': data_mixer_module,
                'type': 'daq_0Dviewer'}]
        importlib.import_module(f'{data_mixer_module.__package__}.daq_0Dviewer_DataMixer')
        plugins_import.extend(mod)

    except Exception as e:
        logger.debug(f'Impossible to import the DataMixer utility plugin: {str(e)}')


    plugins_import.sort(key=lambda mod: mod['name'])
    return plugins_import


def find_model_class(model_module, base: type):
    """ Get the model class of a module of the ``models`` folder of a plugin

    It is the class defined in the module (not imported in it) that derives from ``base`` and that is not itself the
    base class of another one defined there. Deriving from an intermediate class of your own is therefore possible.

    Parameters
    ----------
    model_module: module
        a module of the ``models`` folder of a plugin package
    base: type
        the generic model class of the extension (``PIDModelGeneric``, ``DataMixerModel``...)

    Returns
    -------
    type or None: the model class, None if the module defines none
    """
    candidates = [klass for _, klass in inspect.getmembers(model_module, inspect.isclass)
                  if issubclass(klass, base) and klass is not base and klass.__module__ == model_module.__name__]
    leaves = [klass for klass in candidates if not any(other is not klass and issubclass(other, klass)
                                                       for other in candidates)]
    return leaves[0] if leaves else None


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

