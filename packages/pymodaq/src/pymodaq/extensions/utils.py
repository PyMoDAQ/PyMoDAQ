# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import dataclasses
import importlib
from pathlib import Path
import pkgutil
from typing import TYPE_CHECKING

from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils import logger as logger_module

from pymodaq.extensions.custom_ext import CustomExt
# in older extensions, CustomExt was defined here so this import should stay here also for backcompatibility

logger = logger_module.set_logger(logger_module.get_module_name(__file__))

if TYPE_CHECKING:
    from pymodaq.extensions import ExtensionEnum


def get_ext_modules(path: Path):
    modules = []
    for mod in pkgutil.iter_modules([path]):
        modules.append(mod.name)
    return modules


@dataclasses.dataclass
class Extension:
    name: str
    class_name: str
    klass: type[CustomExt]


def get_extensions() -> dict['ExtensionEnum', Extension]:
    """
    Get pymodaq extensions as an Extension DataClass

    Returns
    -------
    dict:
        dict of Extension DataClass containing the name and class of an extension
        (including internal ones)
    """
    from pymodaq.extensions import internal_extensions, ExtensionEnum
    from aenum import extend_enum

    extension_import = {}
    for ext_name, ext_class in internal_extensions.items():
        extension_import[ExtensionEnum(ext_name)] = Extension(ext_name,
                                               ext_class.__name__,
                                               ext_class)

    discovered_extension = get_entrypoints(group='pymodaq.extensions')
    if len(discovered_extension) > 0:
        for pkg in discovered_extension:
            try:
                module = importlib.import_module(pkg.value)
                modules = get_ext_modules(Path(module.__path__[0]).joinpath('extensions'))
                for mod in modules:
                    try:
                        mod_in = importlib.import_module(f'{pkg.value}.extensions.{mod}')
                        if hasattr(mod_in, 'EXTENSION_NAME'):
                            try:
                                extend_enum(ExtensionEnum, mod_in.CLASS_NAME.upper(), mod_in.EXTENSION_NAME)
                            except TypeError: #already existing no need to add it, could happen if
                                #this function is called several times
                                pass
                            extension_import[ExtensionEnum[mod_in.CLASS_NAME.upper()]] = Extension(
                                mod_in.EXTENSION_NAME,
                                mod_in.CLASS_NAME,
                                getattr(mod_in, mod_in.CLASS_NAME))

                    except Exception as e:  # pragma: no cover
                        logger.warning(f'Impossible to import the {pkg.value}.extensions.{mod} extension: '
                                       f'{str(e)}')
            except Exception as e:
                logger.warning(f'Impossible to import the {pkg.value} package: '
                               f'{str(e)}')

    return extension_import


