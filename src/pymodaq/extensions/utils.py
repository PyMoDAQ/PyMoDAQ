# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import importlib
from pathlib import Path
import pkgutil
import warnings
from typing import Union, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from pymodaq_gui.utils.dock import DockArea
from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils import logger as logger_module
from pymodaq_gui.utils.custom_app import CustomApp

from pymodaq.utils.managers.modules_manager import ModulesManager

logger = logger_module.set_logger(logger_module.get_module_name(__file__))

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


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
    list: list of dict containing the name and module of the found extension

        Each dict is defined with four keys:
            * pkg: the name of the plugin package
            * module: the module name where your extension class is defined
            * class_name: the name of the class defining the extension
            * name: a nice name for your extension to be displayed in the menu

    """
    extension_import = []
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
                            extension_import.append({'pkg': pkg.value, 'module': mod,
                                                     'name': mod_in.EXTENSION_NAME,
                                                     'class_name': mod_in.CLASS_NAME})

                    except Exception as e:  # pragma: no cover
                        logger.warning(f'Impossible to import the {pkg.value}.extensions.{mod} extension: '
                                       f'{str(e)}')
            except Exception as e:
                logger.warning(f'Impossible to import the {pkg.value} package: '
                               f'{str(e)}')

    return extension_import


class CustomExt(CustomApp):

    def __init__(self, parent: Union[DockArea, QtWidgets.QWidget], dashboard: 'DashBoard'):
        super().__init__(parent)

        self.dashboard = dashboard

    @property
    def modules_manager(self) -> ModulesManager:
        """useful tool to interact with DAQ_Moves and DAQ_Viewers

        Will be available if a DashBoard has been set

        Returns
        -------
        ModulesManager
        """
        if self.dashboard is not None:
            return self.dashboard.modules_manager
