

from pymodaq_utils import config as config_mod
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq.extensions.optimizers_base.optimizer import (
    GenericOptimization, OptimizationRunner, optimizer_params)
from pymodaq.extensions.optimizers_base.utils import OptimizerModelDefault, find_key_in_nested_dict
from pymodaq.extensions.optimizers_base.thread_commands import OptimizerToRunner

from pymodaq.extensions.adaptive.loss_function import LossFunctionFactory,LossDim
from pymodaq.extensions.adaptive.utils import AdaptiveAlgorithm, AdaptiveConfig


logger = set_logger(get_module_name(__file__))
config = config_mod.Config()


EXTENSION_NAME = 'AdaptiveScan'
CLASS_NAME = 'AdaptiveOptimization'

PREDICTION_NAMES = list(LossFunctionFactory.keys(LossDim.LOSS_1D))
PREDICTION_PARAMS = [{'title': 'Kind', 'name': 'kind', 'type': 'list',
                      'value': PREDICTION_NAMES[0],
                      'limits': PREDICTION_NAMES}
                     ] + LossFunctionFactory.get(LossDim.LOSS_1D,
                                                 PREDICTION_NAMES[0]).params


class AdaptiveOptimizationRunner(OptimizationRunner):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.PREDICTION:
            utility_params = {k: v for k, v in command.attribute.items() if k != "kind" and k != "tradeoff_actual"}
            #todo pass LossDim enum into here also
            self.optimization_algorithm.set_prediction_function(LossDim.LOSS_1D,
                                                                command.attribute['kind'],
                                                                **utility_params)
        else:
            super().queue_command(command)


class AdaptiveOptimisation(GenericOptimization):
    """ PyMoDAQ extension of the DashBoard to perform the optimization of a target signal
    taken form the detectors as a function of one or more parameters controlled by the actuators.
    """

    runner = AdaptiveOptimizationRunner
    params = optimizer_params(PREDICTION_PARAMS)
    config_saver = AdaptiveConfig

    DISPLAY_BEST = False

    def ini_custom_attributes(self):
        """ Here you can reimplement specific attributes"""
        self._base_name: str = 'Adaptive'

    def validate_config(self) -> bool:
        utility = find_key_in_nested_dict(self.optimizer_config.to_dict(), 'prediction')
        if utility:
            try:
                utility_params = { k : v for k, v in utility.items() \
                                   if k != "kind" and k != "tradeoff_actual" }
                #todo get loss type from params
                LossFunctionFactory.create(LossDim.LOSS_1D,
                                           utility['kind'], **utility_params)
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
            #todo add/get Lossdim from params
            utility_settings.addChildren(LossFunctionFactory.get(LossDim.LOSS_1D,
                                                                 param.value()).params)

    def adaptive_bounds(self):
        return list(self.format_bounds().values())

    def set_algorithm(self):
        self.algorithm = AdaptiveAlgorithm(
            ini_random=self.settings['main_settings', 'ini_random'],
            bounds=self.adaptive_bounds(),
            loss_type=LossDim.LOSS_1D,
            kind=self.settings['main_settings', 'prediction', 'kind'])


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('Adaptive Optimiser')
    preset_file_name = config('presets', f'default_preset_for_scan')

    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, 'AdaptiveScan')

    app.exec()

    return dashboard, extension, win

if __name__ == '__main__':
    main()

