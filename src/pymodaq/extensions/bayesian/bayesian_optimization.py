

from pymodaq_utils import config as config_mod
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand


from pymodaq.extensions.bayesian.utils import BayesianAlgorithm, BayesianConfig

from pymodaq.extensions.bayesian.acquisition import GenericAcquisitionFunctionFactory

from pymodaq.extensions.optimizers_base.optimizer import (
    GenericOptimization, OptimizationRunner, optimizer_params)
from pymodaq.extensions.optimizers_base.utils import OptimizerModelDefault, find_key_in_nested_dict
from pymodaq.extensions.optimizers_base.thread_commands import OptimizerToRunner

logger = set_logger(get_module_name(__file__))
config = config_mod.Config()


EXTENSION_NAME = 'BayesianOptimization'
CLASS_NAME = 'BayesianOptimization'

PREDICTION_NAMES = list(GenericAcquisitionFunctionFactory.keys())
PREDICTION_PARAMS = [{'title': 'Kind', 'name': 'kind', 'type': 'list',
                      'value': PREDICTION_NAMES[0],
                      'limits': PREDICTION_NAMES}
                     ] + GenericAcquisitionFunctionFactory.get(
    PREDICTION_NAMES[0]).params


class BayesianOptimizationRunner(OptimizationRunner):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.PREDICTION:
            utility_params = {k: v for k, v in command.attribute.items() if k != "kind" and k != "tradeoff_actual"}
            self.optimization_algorithm.set_acquisition_function(
                command.attribute['kind'],
                **utility_params)
        else:
            super().queue_command(command)


class BayesianOptimization(GenericOptimization):
    """ PyMoDAQ extension of the DashBoard to perform the optimization of a target signal
    taken form the detectors as a function of one or more parameters controlled by the actuators.
    """

    runner = BayesianOptimizationRunner
    params = optimizer_params(PREDICTION_PARAMS)
    config_saver = BayesianConfig

    def ini_custom_attributes(self):
        """ Here you can reimplement specific attributes"""
        self._base_name: str = 'Bayesian'

    def update_after_actuators_changed(self, actuators: list[str]):
        """ Actions to do after the actuators have been updated
        """
        pass

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
            ini_random=self.settings['main_settings', 'ini_random'],
            bounds=self.format_bounds())


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('Bayesian Optimiser')
    preset_file_name = config('presets', f'default_preset_for_scan')

    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, 'Bayesian')

    app.exec()

    return dashboard, extension, win

if __name__ == '__main__':
    main()

