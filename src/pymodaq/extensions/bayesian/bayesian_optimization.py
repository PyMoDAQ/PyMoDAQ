

from pymodaq_utils import config as config_mod, utils
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand


from pymodaq.extensions.bayesian.utils import BayesianAlgorithm, BayesianConfig

from pymodaq.extensions.bayesian.acquisition import GenericAcquisitionFunctionFactory

from pymodaq.extensions.optimizers_base.optimizer import (
    GenericOptimization, OptimizationRunner, optimizer_params, OptimizerAction)
from pymodaq.extensions.optimizers_base.utils import OptimizerModelDefault, find_key_in_nested_dict
from pymodaq.extensions.optimizers_base.thread_commands import OptimizerToRunner, OptimizerThreadStatus


logger = set_logger(get_module_name(__file__))
config = config_mod.Config()


EXTENSION_NAME = 'BayesianOptimization'
CLASS_NAME = 'BayesianOptimization'

PREDICTION_NAMES = GenericAcquisitionFunctionFactory.usual_names()
PREDICTION_SHORT_NAMES = GenericAcquisitionFunctionFactory.short_names()
PREDICTION_PARAMS = ([{'title': 'Kind', 'name': 'kind', 'type': 'list',
                      'value': PREDICTION_NAMES[0],
                      'limits': {name: short_name for name, short_name in zip(PREDICTION_NAMES, PREDICTION_SHORT_NAMES)}}
                     ] +
                     [{'title': 'Options', 'name': 'options', 'type': 'group',
                       'children': GenericAcquisitionFunctionFactory.get(PREDICTION_SHORT_NAMES[0]).params}]
                     )


class BayesianOptimizationRunner(OptimizationRunner):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.PREDICTION:
            kind = command.attribute.pop('kind')
            self.optimization_algorithm.set_acquisition_function(
                kind,
                **command.attribute)
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

    def update_prediction_function(self):
        """ Get the selected prediction function options and pass them to the Runner

        Should be reimplemented in real Optimizer implementation
        """
        utility_settings = self.settings.child('main_settings', 'prediction')

        kind = utility_settings.child('kind').value()
        uparams = {child.name() : child.value() for child in utility_settings.child('options').children()}
        uparams['kind'] = kind
        self.command_runner.emit(
            utils.ThreadCommand(OptimizerToRunner.PREDICTION, uparams))


    def validate_config(self) -> bool:
        utility = find_key_in_nested_dict(self.optimizer_config.to_dict(), 'prediction')
        if utility:
            try:
                kind = utility.pop('kind', None)
                if kind is not None:
                    GenericAcquisitionFunctionFactory.create(kind, **utility)
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
            param.parent().child('options').clearChildren()
            param.parent().child('options').addChildren(
                GenericAcquisitionFunctionFactory.get(param.value()).params)

    def set_algorithm(self):
        self.algorithm = BayesianAlgorithm(
            ini_random=self.settings['main_settings', 'ini_random'],
            bounds=self.format_bounds(),
            actuators=self.modules_manager.selected_actuators_name)

    def thread_status(self, status: utils.ThreadCommand):
        super().thread_status(status)
        if status.command == OptimizerThreadStatus.TRADE_OFF:
            self.settings.child('main_settings', 'prediction', 'options', 'tradeoff_actual').setValue(status.attribute)


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('Bayesian Optimiser')
    #preset_file_name = config('presets', f'beam_steering')

    dashboard, extension, win = load_dashboard_with_preset('beam_steering', 'Bayesian')

    app.exec()

    return dashboard, extension, win

if __name__ == '__main__':
    main()

