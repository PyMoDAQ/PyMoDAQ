from typing import List,  Optional
import tempfile
from pathlib import Path

from qtpy import QtWidgets, QtCore
import time
import numpy as np

from pymodaq.utils.data import DataToExport, DataToActuators, DataCalculated, DataActuator
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_utils import utils

from pymodaq_utils import config as config_mod
from pymodaq_utils.enums import BaseEnum


from pymodaq_gui.config import ConfigSaverLoader
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq_gui.utils import QLED
from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui import utils as gutils
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq_data.h5modules.data_saving import DataEnlargeableSaver


from pymodaq.extensions.bayesian.utils import (
    BayesianAlgorithm, StopType, StoppingParameters)

from pymodaq.extensions.bayesian.acquisition import GenericAcquisitionFunctionFactory


from pymodaq.extensions.optimisers_base.optimizer import (
    GenericOptimisation, OptimizerModelGeneric, OptimiserConfig,
    get_optimizer_models, find_key_in_nested_dict)
from pymodaq.extensions.optimisers_base.utils import OptimizerModelDefault

EXTENSION_NAME = 'BayesianOptimisation'
CLASS_NAME = 'BayesianOptimisation'

logger = set_logger(get_module_name(__file__))
config = config_mod.Config()


class BayesianOptimisation(GenericOptimisation):
    """ PyMoDAQ extension of the DashBoard to perform the optimization of a target signal
    taken form the detectors as a function of one or more parameters controlled by the actuators.
    """

    acquisition_functions_names = list(GenericAcquisitionFunctionFactory.keys())

    prediction_params = [{'title': 'Kind', 'name': 'kind', 'type': 'list',
                          'value': acquisition_functions_names[0],
                          'limits': acquisition_functions_names}
                         ] + GenericAcquisitionFunctionFactory.get(
        acquisition_functions_names[0]).params


    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

    def validate_config(self) -> bool:
        utility = find_key_in_nested_dict(self.optimizer_config.to_dict(), 'prediction')
        if utility:
            try:
                utility_params = { k : v for k, v in utility.items() \
                                   if k != "kind" and k != "tradeoff_actual" }
                GenericAcquisitionFunctionFactory.create(utility['kind'], **utility_params)
            except ValueError:
                return False

        return True

    def value_changed(self, param):
        """ to be subclassed for actions to perform when one of the param's value in self.settings is changed

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        super().value_changed(param)
        if param.name() == 'kind':
            utility_settings = self.settings.child('main_settings', 'prediction')
            old_children = utility_settings.children()[1:]
            for child in old_children:
                utility_settings.removeChild(child)
            utility_settings.addChildren(GenericAcquisitionFunctionFactory.get(param.value()).params)

    def set_algorithm(self):
        self.algorithm = BayesianAlgorithm(
            # acquisition=self.settings['main_settings', 'prediction', 'kind'],
            ini_random=self.settings['main_settings', 'ini_random'],
            bounds=self.format_bounds())


def main(init_qt=True):
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('Bayesian Optimiser')
    preset_file_name = config('presets', f'default_preset_for_scan')

    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, 'Bayesian')

    app.exec()

    return dashboard, extension, win

if __name__ == '__main__':
    main()

