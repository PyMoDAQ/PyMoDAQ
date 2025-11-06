from pymodaq_gui.messenger import messagebox
from pymodaq_utils import utils
from pymodaq_utils import config as config_mod
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq.extensions.optimizers_base.optimizer import (
    GenericOptimization, OptimizationRunner, optimizer_params, OptimizerAction, StopType)
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
        [{'title': 'Options', 'name': 'options', 'type': 'group',
          'children': LossFunctionFactory.get(STARTING_LOSS_DIM, PREDICTION_NAMES[0]).params}]
)


class AdaptiveOptimizationRunner(OptimizationRunner):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.PREDICTION:
            kind = command.attribute.pop('kind')
            lossdim = command.attribute.pop('lossdim')
            self.optimization_algorithm.set_prediction_function(lossdim, kind, **command.attribute)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_action(OptimizerAction.SAVE).trigger()
        self.settings.child('main_settings', 'ini_random').hide()
        self.settings.child('main_settings', 'stopping', 'tolerance').hide()
        self.settings.child('main_settings', 'stopping', 'npoints').hide()
        self.settings.child('main_settings', 'stopping', 'stop_type').setLimits(
            [StopType.NONE.value, StopType.ITER.value])

    def ini_custom_attributes(self):
        """ Here you can reimplement specific attributes"""
        self._base_name: str = 'Adaptive'

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
            try:
                self.settings.child('main_settings', 'prediction', 'kind').setLimits(
                    LossFunctionFactory.keys(param.value())
                )
            except Exception as e:
                logger.debug('Warning: Error while trying to infer the kind of loss, may be because limits just changed')
        elif param.name() == 'kind':
            utility_settings = self.settings.child('main_settings', 'prediction')
            utility_settings.child('options').clearChildren()
            try:
                params = LossFunctionFactory.get(utility_settings['lossdim'],
                                                 param.value()).params
                utility_settings.child('options').addChildren(params)
            except (KeyError, ValueError) as e:
                logger.debug('Warning: Error while trying to populate options for loss, may be because limits for'
                             ' kind setting just changed')

    def update_prediction_function(self):
        utility_settings = self.settings.child('main_settings', 'prediction')
        try:
            uparams = {child.name() : child.value() for child in utility_settings.child('options').children()}
            uparams['kind'] = utility_settings['kind']
            uparams['lossdim'] = utility_settings['lossdim']

            self.command_runner.emit(
                utils.ThreadCommand(OptimizerToRunner.PREDICTION, uparams))
        except (KeyError, ValueError, AttributeError) as e:
            pass
            print(e)

    def update_after_actuators_changed(self, actuators: list[str]):
        """ Actions to do after the actuators have been updated
        """
        try:#see if there is some registered loss function for the defined type
            self.settings.child('main_settings', 'prediction',
                                'lossdim').setValue(LossDim.get_enum_from_dim_as_int(len(actuators)))
            self.update_prediction_function()

            LossFunctionFactory.create(self.settings['main_settings', 'prediction',
                                                           'lossdim'],
                                       self.settings['main_settings', 'prediction',
                                                           'kind'])
            self.get_action(OptimizerAction.INI_RUNNER).setEnabled(True)

        except ValueError as e:
            self.get_action(OptimizerAction.INI_RUNNER).setEnabled(False)
            messagebox(title='Warning',
                       text=f'You cannot select [{actuators}] as no corresponding Loss function exists')

    def set_algorithm(self):
        self.algorithm = AdaptiveAlgorithm(
            ini_random=1,
            bounds=self.format_bounds(),
            actuators=self.modules_manager.selected_actuators_name,
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

