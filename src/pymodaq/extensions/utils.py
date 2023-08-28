# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import importlib
from pathlib import Path
import pkgutil

from pymodaq.utils import logger as logger_module
from pymodaq.utils.daq_utils import get_entrypoints
logger = logger_module.set_logger(logger_module.get_module_name(__file__))


def get_ext_modules(path: Path):
    modules = []
    for mod in pkgutil.iter_modules([path]):
        modules.append(mod.name)
    return modules


def get_extensions():
    """
    Get pymodaq extensions as a list

    Returns
    -------
    list: list of dict containting the name and module of the found extension
    """
    extension_import = []
    discovered_extension = get_entrypoints(group='pymodaq.extensions')
    if len(discovered_extension) > 0:
        for pkg in discovered_extension:
            try:
                module = importlib.import_module(pkg.value)
                modules = get_ext_modules(Path(module.__path__[0]).joinpath('extensions'))
                for mod in modules:
                    mod_in = importlib.import_module(f'{pkg.value}.extensions.{mod}')
                    extension_import.append({'pkg': pkg.value, 'module': mod, 'name': mod_in.EXTENSION_NAME,
                                             'class_name': mod_in.class_name})

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value}.extensions.{mod} extension: {str(e)}')

    return extension_import
