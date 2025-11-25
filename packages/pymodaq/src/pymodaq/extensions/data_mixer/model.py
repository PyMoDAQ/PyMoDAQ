import dataclasses
from typing import List, TYPE_CHECKING
import importlib
import inspect
import pkgutil
import warnings
from pathlib import Path
from typing import Union, List

import numpy as np  # to be imported within models

from pymodaq_utils.utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data.data import DataToExport

from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter
from pymodaq_gui.config_saver_loader import ConfigSaverLoader


logger = set_logger(get_module_name(__file__))

if TYPE_CHECKING:
    from pymodaq.extensions.data_mixer import DataMixer
    from pymodaq.utils.managers.modules_manager import ModulesManager


class DataMixerModel:

    detectors_name: List[str] = []
    params = []

    def __init__(self, data_mixer: 'DataMixer'):
        self.data_mixer = data_mixer
        self.modules_manager: ModulesManager = data_mixer.modules_manager
        self.settings: Parameter = self.data_mixer.settings.child('models', 'model_params')


    def ini_model_base(self):
        """ Method to add things that should be executed before instantiating the model"""
        self.ini_model()

    def ini_model(self):
        pass

    def update_settings(self, param: Parameter):
        pass

    def process_dte(self, measurements: DataToExport) -> DataToExport:
        """
        Convert the measurements in the units to be fed to the PID (same dimensionality as the setpoint)
        Parameters
        ----------
        measurements: DataToExport
         DataToExport object from which the model extract a value of the same units as the setpoint

        Returns
        -------
        DataToExport: the converted input as 0D DataCalculated stored in a DataToExport
        """
        raise NotImplementedError


@dataclasses.dataclass
class PkgMock:
    value: str


def get_models(model_name=None) -> list[dict[(str, str), (str, type)]]:
    """
    Get DataMixer Models

    Returns
    -------
    list: list of dict containing the name and python module of the found models

    Example
    -------
    model = [{'name': 'MyModel', 'class': DataModel}]
    """
    models_import = []
    discovered_models = list(get_entrypoints(group='pymodaq.models'))
    discovered_models.append(PkgMock('pymodaq.extensions.data_mixer'))
    if len(discovered_models) > 0:
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        model_module = importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        classes = inspect.getmembers(model_module, inspect.isclass)
                        for name, klass in classes:
                            if klass.__base__ is DataMixerModel:
                                models_import.append({'name': mod.name, 'module': model_module, 'class': klass})
                                break

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)
