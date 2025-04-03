
from pymodaq_utils import utils
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

STARTING_LOSS_DIM = LossDim.LOSS_1D

PREDICTION_NAMES = list(LossFunctionFactory.keys(STARTING_LOSS_DIM))
PREDICTION_PARAMS = (
        [{'title': 'LossDim', 'name': 'lossdim', 'type': 'str',
          'value': LossDim.LOSS_1D, 'readonly': True},
         {'title': 'Kind', 'name': 'kind', 'type': 'list',
          'value': PREDICTION_NAMES[0],
          'limits': PREDICTION_NAMES}] +
        LossFunctionFactory.get(STARTING_LOSS_DIM,
                                PREDICTION_NAMES[0]).params)


class AdaptiveOptimizationRunner(OptimizationRunner):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.PREDICTION:
            utility_params = {k: v for k, v in command.attribute.items()
                              if k not in ("kind", "tradeoff_actual", 'lossdim')}

            self.optimization_algorithm.set_prediction_function(command.attribute['lossdim'],
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
        self.settings.child('main_settings', 'ini_random').hide()

    def validate_config(self) -> bool:
        utility = find_key_in_nested_dict(self.optimizer_config.to_dict(), 'prediction')
        if utility:
            try:
                utility_params = { k : v for k, v in utility.items() \
                                   if k not in ("kind", "tradeoff_actual", 'lossdim') }
                LossFunctionFactory.create(utility['lossdim'],
                                           utility['kind'], **utility_params)
            except (ValueError, KeyError):
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
        if param.name() == 'lossdim':
            self.settings.child('main_settings', 'prediction', 'kind').setLimits(
                LossFunctionFactory.keys(param.value())
            )

        elif param.name() == 'kind':
            utility_settings = self.settings.child('main_settings', 'prediction')
            old_children = utility_settings.children()[2:]
            for child in old_children:
                utility_settings.removeChild(child)
            try:
                params = LossFunctionFactory.get(utility_settings['lossdim'],
                                                 param.value()).params
                utility_settings.addChildren(params)
            except (KeyError, ValueError):
                pass

    def update_prediction_function(self):
        utility_settings = self.settings.child('main_settings', 'prediction')
        try:
            uparams = {child.name() : child.value() for child in utility_settings.children()}
            LossFunctionFactory.get(uparams['lossdim'], uparams['kind'])
            self.command_runner.emit(
                utils.ThreadCommand(OptimizerToRunner.PREDICTION, uparams))
        except (KeyError, ValueError):
            pass

    def update_after_actuators_changed(self, actuators: list[str]):
        """ Actions to do after the actuators have been updated
        """
        self.settings.child('main_settings', 'prediction',
                            'lossdim').setValue(LossDim.get_enum_from_dim_as_int(len(actuators)))
        self.update_prediction_function()

    def adaptive_bounds(self):
        return list(self.format_bounds().values())

    def set_algorithm(self):
        self.algorithm = AdaptiveAlgorithm(
            ini_random=1,
            bounds=self.adaptive_bounds(),
            loss_type=LossDim(self.settings['main_settings', 'prediction', 'lossdim']),
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

