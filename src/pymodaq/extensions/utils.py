# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import importlib
from pymodaq.utils import logger as logger_module
from pymodaq.utils.daq_utils import get_entrypoints
logger = logger_module.set_logger(logger_module.get_module_name(__file__))


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
                if hasattr(module, 'NICE_NAME'):
                    name = module.NICE_NAME
                else:
                    name = pkg.value
                extension = {'name': name, 'module': module}
                extension_import.append(extension)

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    return extension_import
