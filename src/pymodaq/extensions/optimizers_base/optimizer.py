import abc
from typing import List,  Optional
import tempfile
from pathlib import Path


from qtpy import QtWidgets, QtCore
import time
import numpy as np

from collections import OrderedDict


from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_gui.messenger import messagebox
from pymodaq_utils import utils

from pymodaq_utils.enums import BaseEnum, StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
try:
    from pymodaq_gui.config_saver_loader import ConfigSaverLoader
except ModuleNotFoundError:
    from pymodaq_gui.config import ConfigSaverLoader #backcompatibility

from pymodaq_utils.config import Config as ConfigUtils

from pymodaq_data.h5modules.data_saving import DataEnlargeableSaver

from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq_gui.utils import QLED
from pymodaq_gui.utils.widgets.spinbox import QSpinBox_ro
from pymodaq_gui import utils as gutils
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq.utils.data import DataToExport, DataToActuators, DataCalculated, DataActuator
from pymodaq.post_treatment.load_and_plot import LoaderPlotter
from pymodaq.extensions.utils import CustomExt

from pymodaq.utils.h5modules import module_saving
from pymodaq.utils import config as config_mod

from pymodaq.extensions.optimizers_base.utils import (
    get_optimizer_models, OptimizerModelGeneric,
    GenericAlgorithm, StopType, StoppingParameters,
    OptimizerConfig, individual_as_dta, individual_as_dte)
from pymodaq.extensions.optimizers_base.thread_commands import OptimizerToRunner, OptimizerThreadStatus


logger = set_logger(get_module_name(__file__))
config = config_mod.Config()
config_utils = ConfigUtils()

PREDICTION_PARAMS = []  # to be subclassed in real optimizer implementations
MODELS = get_optimizer_models()


class OptimizerAction(StrEnum):
    QUIT = 'quit'
    INI_MODEL = 'ini_model'
    MODELS = 'models'
    SAVE = 'save'
    INI_RUNNER = 'ini_runner'
    RUN = 'run'
    RESTART = 'restart'
    STOP = 'stop'
    GO_TO_BEST = 'gotobest'
    GO_TO = 'goto'


class DataNames(StrEnum):
    Fitness = 'fitness'
    Individual = 'individual'
    ProbedData = 'probed_data'
    Actuators = 'actuators'
    Tradeoff = 'tradeoff'


def optimizer_params(prediction_params: list[dict]):
    return [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': True, 'type': 'group',
         'children': [
             {'title': 'Prediction Function:', 'name': 'prediction', 'expanded': False, 'type': 'group',
              'children': prediction_params

              },
             {'title': 'Stopping Criteria:', 'name': 'stopping', 'expanded': False, 'type': 'group',
              'children': [
                  {'title': 'Niteration', 'name': 'niter', 'type': 'int',
                   'value': config('optimizer', 'n_iter'), 'min': 5},
                  {'title': 'Type:', 'name': 'stop_type', 'type': 'list',
                   'limits': StopType.values(), 'value': str(StopType.ITER),
                   'tip': StopType.ITER.tip()},
                  {'title': 'Tolerance', 'name': 'tolerance', 'type': 'slide', 'value': 1e-2,
                   'min': 1e-8, 'max': 1, 'subtype': 'log', },
                  {'title': 'Npoints', 'name': 'npoints', 'type': 'int', 'value': 5, 'min': 1},
              ]},
             {'title': 'Ini. Random Points', 'name': 'ini_random', 'type': 'int', 'value': 5},
             {'title': 'bounds', 'name': 'bounds', 'type': 'group', 'children': []},
         ]},

        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True,
         'children': [
             {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
              'limits': [d['name'] for d in MODELS]},
             {'title': 'Ini Model', 'name': 'ini_model', 'type': 'action', },
             {'title': 'Ini Algo', 'name': 'ini_runner', 'type': 'action', 'enabled': False},
             {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},
         ]},
        {'title': 'Move settings:', 'name': 'move_settings', 'expanded': True, 'type': 'group',
         'visible': False, 'children': [
            {'title': 'Units:', 'name': 'units', 'type': 'str', 'value': ''}]},

    ]


class DataToActuatorsOpti(DataToActuators):
    """ Specific class including the step in the optimization loop for further use"""
    ind_iter: int
    def __init__(self, *args, ind_iter=0, **kwargs):
        super().__init__(*args, ind_iter=ind_iter, **kwargs)

    def __repr__(self):
        return f'{super().__repr__()} iter:{self.ind_iter}'



class OptimizationRunner(QtCore.QObject):
    algo_live_plot_signal = QtCore.Signal(DataToExport)
    algo_finished = QtCore.Signal(DataToExport)
    saver_signal = QtCore.Signal(DataToActuatorsOpti)

    runner_command = QtCore.Signal(utils.ThreadCommand)

    def __init__(self, model_class: OptimizerModelGeneric, modules_manager: ModulesManager,
                 algorithm: GenericAlgorithm, stopping_params: StoppingParameters):
        super().__init__()

        self.det_done_datas: DataToExport = None
        self.input_from_dets: float = None
        self.outputs: List[np.ndarray] = []
        self.output_to_actuators: DataToActuators = None
        self.dte_actuators: DataToExport = None
        self.stopping_params: StoppingParameters = stopping_params

        self.model_class: OptimizerModelGeneric = model_class
        self.modules_manager: ModulesManager = modules_manager

        self.running = True
        self.converged = False
        self._ind_iter = -1

        self.optimization_algorithm: GenericAlgorithm = algorithm


    def queue_command(self, command: utils.ThreadCommand):
        """
        """
        if command.command == OptimizerToRunner.RUN:
            if command.attribute is None:
                command.attribute = {}
            self.run_opti(**command.attribute)

        elif command.command == OptimizerToRunner.PAUSE:
            self.running = False

        elif command.command == OptimizerToRunner.STOP:
            self.converged = True

        elif command.command == OptimizerToRunner.STOPPING:
            self.stopping_params: StoppingParameters = command.attribute

        elif command.command == OptimizerToRunner.BOUNDS:
            self.optimization_algorithm.bounds = command.attribute

        elif command.command == OptimizerToRunner.RESTART:
            self.optimization_algorithm = command.attribute
            self._ind_iter = -1

    def run_opti(self, sync_detectors=True, sync_acts=True):
        """Start the optimization loop

        Parameters
        ----------
        sync_detectors: (bool) if True will make sure all selected detectors (if any) all got their data before calling
            the model
        sync_acts: (bool) if True will make sure all selected actuators (if any) all reached their target position
         before calling the model
        """
        self.running = True
        self.converged = False
        try:
            if sync_detectors:
                self.modules_manager.connect_detectors()
            if sync_acts:
                self.modules_manager.connect_actuators()

            self.current_time = time.perf_counter()
            logger.info('Optimisation loop starting')
            while self.running:
                self._ind_iter += 1

                next_target: dict[str, float] = self.optimization_algorithm.ask()

                self.outputs = next_target
                self.output_to_actuators: DataToActuators = \
                    self.model_class.convert_output(
                        self.outputs,
                        best_individual=self.optimization_algorithm.best_individual
                    )
                for dwa in self.output_to_actuators:
                    dwa.origin = DataNames.Actuators

                self.modules_manager.move_actuators(self.output_to_actuators,
                                                    self.output_to_actuators.mode,
                                                    polling=sync_acts)

                # Do the evaluation (measurements)
                self.det_done_datas = self.modules_manager.grab_data()
                self.input_from_dets = self.model_class.convert_input(self.det_done_datas)

                #log data
                self.runner_command.emit(
                    utils.ThreadCommand(OptimizerThreadStatus.ADD_DATA,))

                # Run the algo internal mechanic
                self.optimization_algorithm.tell(self.input_from_dets)

                dte_algo = individual_as_dte(self.optimization_algorithm.best_individual,
                                             self.modules_manager.actuators,
                                             DataNames.Individual)
                dte_algo.append([DataCalculated(DataNames.Fitness,
                                               data=[np.atleast_1d(self.optimization_algorithm.best_fitness)]),
                                 ])
                dte_algo.append(self.output_to_actuators)
                dte_algo.append(DataCalculated(DataNames.ProbedData,
                                               data=[np.array([self.input_from_dets])],
                                               origin='algo'))
                self.algo_live_plot_signal.emit(dte_algo)

                
                self.saver_signal.emit(DataToActuatorsOpti(DataNames.Actuators,
                                                           data = self.output_to_actuators.deepcopy().data,
                                                           mode=self.output_to_actuators.mode,
                                                           ind_iter=self._ind_iter))

                self.optimization_algorithm.update_prediction_function()
                self.runner_command.emit(
                    utils.ThreadCommand(OptimizerThreadStatus.TRADE_OFF, attribute=self.optimization_algorithm.tradeoff))


                self.converged = (self.converged or
                                  self.optimization_algorithm.stopping(self._ind_iter, self.stopping_params))
                if self.converged:
                    break

                self.current_time = time.perf_counter()
                QtWidgets.QApplication.processEvents()
                QtWidgets.QApplication.processEvents()
            logger.info('Optimisation loop exiting')
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

            if self.converged:
                self.algo_finished.emit(dte_algo)

        except Exception as e:
            logger.exception(str(e))


class GenericOptimization(CustomExt):
    """ PyMoDAQ extension of the DashBoard to perform the optimization of a target signal
    taken form the detectors as a function of one or more parameters controlled by the actuators.
    """

    command_runner = QtCore.Signal(utils.ThreadCommand)
    explored_viewer_name = f'algo/{DataNames.ProbedData}'
    optimization_done_signal = QtCore.Signal(DataToExport)

    runner = OptimizationRunner  # replace in real implementation if customization is needed
    DISPLAY_BEST = True

    params = optimizer_params(PREDICTION_PARAMS)

    config_saver = OptimizerConfig  #to be redefined in real implementation if needed

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        self._ini_runner = False

        self.algorithm: Optional[GenericAlgorithm] = None
        self.viewer_observable: Optional[ViewerDispatcher] = None
        self.model_class: Optional[OptimizerModelGeneric] = None
        self._save_main_settings = True

        self.modules_manager.actuators_changed[list].connect(self.update_actuators)
        self.modules_manager.settings.child('data_dimensions').setOpts(expanded=False)
        self.modules_manager.settings.child('actuators_positions').setOpts(expanded=False)

        self._h5saver: H5Saver = None
        self.h5saver.settings.child('do_save').hide()
        self.h5saver.settings.child('custom_name').hide()
        self.h5saver.new_file_sig.connect(self.create_new_file)

        self.setup_ui()

        self.optimizer_config = self.config_saver()

        self.mainsettings_saver_loader = ConfigSaverLoader(
            self.settings.child('main_settings'), self.optimizer_config)

        self._base_name: str = None

        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None
        self.enlargeable_saver: DataEnlargeableSaver = None
        self.live_plotter = LoaderPlotter(self.dockarea)

        self._module_and_data_saver: module_saving.OptimizerSaver = None

        self._ind_iter: int = 0
        self.enl_index = 0

        self.settings.child('models', 'ini_model').sigActivated.connect(
            self.get_action(OptimizerAction.INI_MODEL).trigger)

        self.settings.child('models', 'ini_runner').sigActivated.connect(
            self.get_action(OptimizerAction.INI_RUNNER).trigger)

        self.ini_custom_attributes()

        if len(MODELS) == 1:
            self.get_action(OptimizerAction.INI_MODEL).trigger()


    @property
    def title(self):
        return f'{self.__class__.__name__}'

    def ini_custom_attributes(self):
        """ Here you can reimplement specific attributes"""
        self._base_name: str = 'Optimizer'  # base name used for naming the hdf5 file

    @property
    def h5saver(self):
        if self._h5saver is None:
            self._h5saver = H5Saver(save_type='optimizer', backend=config_utils('general', 'hdf5_backend'))
            self._h5saver.settings.child('base_name').setValue('Optimizer')
        if self._h5saver.h5_file is None:
            self._h5saver.init_file(update_h5=True)
        if not self._h5saver.isopen():
            self._h5saver.init_file(addhoc_file_path=self._h5saver.settings['current_h5_file'])
        return self._h5saver

    @h5saver.setter
    def h5saver(self, h5saver_temp: H5Saver):
        self._h5saver = h5saver_temp

    @property
    def module_and_data_saver(self):
        if not self._module_and_data_saver.h5saver.isopen():
            self._module_and_data_saver.h5saver = self.h5saver
        return self._module_and_data_saver

    @module_and_data_saver.setter
    def module_and_data_saver(self, mod: module_saving.OptimizerSaver):
        self._module_and_data_saver = mod
        self._module_and_data_saver.h5saver = self.h5saver

    def create_new_file(self, new_file):
        if new_file:
            self.close_file()
        self.module_and_data_saver.h5saver = self.h5saver  # force all control modules to update their h5saver

    def close_file(self):
        self.h5saver.close_file()

    def add_data(self, dta: DataToActuatorsOpti):
        if self.is_action_checked(OptimizerAction.SAVE):
            self.module_and_data_saver.add_data(axis_values=[dwa[0] for dwa in dta],
                                                init_step=dta.ind_iter == 0)

    @abc.abstractmethod
    def validate_config(self) -> bool:
        pass

    @property
    def config_path(self) -> Path:
        return self.optimizer_config.config_path

    def setup_docks(self):
        """
        to be subclassed to setup the docks layout
        for instance:

        self.docks['ADock'] = gutils.Dock('ADock name)
        self.dockarea.addDock(self.docks['ADock"])
        self.docks['AnotherDock'] = gutils.Dock('AnotherDock name)
        self.dockarea.addDock(self.docks['AnotherDock"], 'bottom', self.docks['ADock"])

        See Also
        ########
        pyqtgraph.dockarea.Dock
        """
        self.docks['saving'] = gutils.Dock('Saving')
        self.docks['saving'].addWidget(self.h5saver.settings_tree)
        self.dockarea.addDock(self.docks['saving'])

        self.docks['settings'] = gutils.Dock('Settings')
        self.dockarea.addDock(self.docks['settings'], 'below', self.docks['saving'])
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.docks['settings'].addWidget(splitter)
        splitter.addWidget(self.modules_manager.settings_tree)
        splitter.addWidget(self.settings_tree)
        self.modules_manager.show_only_control_modules(True)
        self.modules_manager.settings_tree.setEnabled(False)

        splitter.setSizes((int(self.dockarea.height() / 2),
                           int(self.dockarea.height() / 2)))
        if self.DISPLAY_BEST:
            widget_observable = QtWidgets.QWidget()
            widget_observable.setLayout(QtWidgets.QHBoxLayout())
            observable_dockarea = gutils.DockArea()
            widget_observable.layout().addWidget(observable_dockarea)
            self.viewer_observable = ViewerDispatcher(observable_dockarea, direction='bottom')
            self.docks['observable'] = gutils.Dock('Observable')
            self.dockarea.addDock(self.docks['observable'], 'right', self.docks['settings'])
            self.docks['observable'].addWidget(widget_observable)

        if len(MODELS) != 0:
            self.get_set_model_params(MODELS[0]['name'])


        self._statusbar = QtWidgets.QStatusBar()
        self.mainwindow.setStatusBar(self._statusbar)
        self.populate_status_bar()


    def populate_status_bar(self):
        self._status_message_label = QtWidgets.QLabel('Initializing')
        self._optimizing_step = QSpinBox_ro()
        self._optimizing_step.setToolTip('Current Optimizing step')

        self._optimizing_done_LED = QLED()
        self._optimizing_done_LED.set_as_false()
        self._optimizing_done_LED.clickable = False
        self._optimizing_done_LED.setToolTip('Scan done state')
        self._statusbar.addPermanentWidget(self._status_message_label)

        self._statusbar.addPermanentWidget(self._optimizing_step)
        self._statusbar.addPermanentWidget(self._optimizing_done_LED)


    def get_set_model_params(self, model_name):
        self.settings.child('models', 'model_params').clearChildren()
        if len(MODELS) > 0:
            model_class = utils.find_dict_in_list_from_key_val(MODELS, 'name', model_name)['class']
            params = getattr(model_class, 'params')
            self.settings.child('models', 'model_params').addChildren(params)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        '''
        to be subclassed
        create menu for actions contained into the self.actions_manager, for instance:

        For instance:

        file_menu = self.menubar.addMenu('File')
        self.actions_manager.affect_to('load', file_menu)
        self.actions_manager.affect_to('save', file_menu)

        file_menu.addSeparator()
        self.actions_manager.affect_to('quit', file_menu)
        '''
        pass

    def value_changed(self, param):
        ''' to be subclassed for actions to perform when one of the param's value in self.settings is changed

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        '''
        if param.name() == 'model_class':
            self.get_set_model_params(param.value())
            self.get_action(OptimizerAction.MODELS).setCurrentText(param.value())
        elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
            if self.model_class is not None:
                self.model_class.update_settings(param)
        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'bounds'), []):
            self.update_bounds()
        elif param.name() in putils.iter_children(
            self.settings.child('main_settings', 'stopping'), []):
            self.update_stopping_criteria()
            if param.name() == 'stop_type' and param.value() is not None:
                self.settings.child('main_settings', 'stopping', 'stop_type').setOpts(
                    tip=StopType(param.value()).tip())
        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'prediction'), []):
            if param.name() != 'tradeoff_actual':
                self.update_prediction_function()

        if self._save_main_settings and self.model_class is not None and param.name() in putils.iter_children(
               self.settings.child('main_settings'), []):
            self.mainsettings_saver_loader.save_config()

    def update_prediction_function(self):
        """ Get the selected prediction function options and pass them to the Runner

        Should be reimplemented in real Optimizer implementation
        Something like:

        utility_settings = self.settings.child('main_settings', 'prediction')
        kind = utility_settings.child('kind').value()
        uparams = {child.name() : child.value() for child in utility_settings.child('options').children()}
        uparams['kind'] = kind
        self.command_runner.emit(
            utils.ThreadCommand(OptimizerToRunner.PREDICTION, uparams))
        """
        pass

    def get_stopping_parameters(self) -> StoppingParameters:
        stopping_settings = self.settings.child('main_settings', 'stopping')
        stopping_params = StoppingParameters(stopping_settings['niter'],
                                             stopping_settings['stop_type'],
                                             stopping_settings['tolerance'],
                                             stopping_settings['npoints'])
        return stopping_params

    def update_stopping_criteria(self):
        self.command_runner.emit(
            utils.ThreadCommand(OptimizerToRunner.STOPPING, self.get_stopping_parameters()))

    def update_bounds(self):
        bounds = {}
        for child in self.settings.child('main_settings', 'bounds').children():
            bounds[child.name()] = (child['min'], child['max'])

        self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.BOUNDS, bounds))

    def setup_actions(self):
        logger.debug('setting actions')
        self.add_action(OptimizerAction.QUIT, 'Quit', 'close2', "Quit program")
        combo_model = QtWidgets.QComboBox()
        combo_model.addItems([model['name'] for  model in MODELS])
        self.add_widget(OptimizerAction.MODELS, combo_model, tip='List of available models')
        self.add_action(OptimizerAction.INI_MODEL, 'Init Model', 'ini')
        self.add_widget('model_led', QLED, toolbar=self.toolbar)
        self.add_action(OptimizerAction.SAVE, 'Save?', 'SaveAs', tip='If checked, data will be saved',
                        checkable=True)
        self.add_action(OptimizerAction.INI_RUNNER, 'Init the Optimisation Algorithm', 'ini', checkable=True,
                        enabled=False)
        self.add_widget('runner_led', QLED, toolbar=self.toolbar)
        self.add_action(OptimizerAction.RUN, 'Run Optimisation', 'run2', checkable=True, enabled=False)
        self.add_action(OptimizerAction.RESTART, 'Restart algo', 'Refresh2', checkable=False, enabled=False)
        self.add_action(OptimizerAction.STOP, 'Stop algo', 'stop', checkable=False, enabled=False,
                        tip='Stop algo and go to best individual')

        self.add_action(OptimizerAction.GO_TO_BEST, 'Go to best', 'Rendezvous', enabled=False,
                        tip='Go to the position optimizing the signal')
        self.add_action(OptimizerAction.GO_TO, 'Go to ', 'move_contour', enabled=False, checkable=True,
                        tip='Go to the double clicked position in the plot')
        logger.debug('actions set')

    def connect_things(self):
        logger.debug('connecting things')
        self.connect_action(OptimizerAction.QUIT, self.quit)
        self.connect_action('models', self.update_model_settings_from_action,
                            signal_name='currentTextChanged')

        self.connect_action(OptimizerAction.SAVE, self.do_save)
        self.connect_action(OptimizerAction.INI_MODEL, self.ini_model)
        self.connect_action(OptimizerAction.INI_RUNNER, self.ini_optimization_runner)
        self.connect_action(OptimizerAction.RUN, self.run_optimization)
        self.connect_action(OptimizerAction.RESTART, self.restart_algo)
        self.connect_action(OptimizerAction.STOP, self.stop_algo)
        self.connect_action(OptimizerAction.GO_TO_BEST, self.go_to_best)
        self.connect_action(OptimizerAction.GO_TO, self.allow_go_to)
        self.h5saver.new_file_sig.connect(self.create_new_file)


    def update_model_settings_from_action(self, model: str):
        self.settings.child('models', 'model_class').setValue(model)

    def go_to_best(self):
        best_individual = self.algorithm.best_individual
        if best_individual is not None:
            actuators = self.modules_manager.actuators
            dte_act = DataToActuators('best',
                                      data=[
                                          DataActuator(actuators[ind].title,
                                                       data=float(best_individual[actuators[ind].title]),
                                                       units=actuators[ind].units)
                                          for ind in range(len(best_individual))
                                      ],
                                      mode='abs')
            self.modules_manager.connect_actuators(True)
            self.modules_manager.move_actuators(dte_act, polling=True)
            self.modules_manager.connect_actuators(False)

    def allow_go_to(self, enable=True):
        if len(self.live_plotter.viewers) > 0:
            if enable:
                self.live_plotter.viewers[0].sig_double_clicked.connect(self.go_to)
            else:
                self.live_plotter.viewers[0].sig_double_clicked.disconnect(self.go_to)

    def go_to(self, *positions):
        actuators = self.modules_manager.actuators
        dte_act = DataToActuators('best',
                                  data=[
                                      DataActuator(actuators[ind].title,
                                                   data=float(positions[ind]),
                                                   units=actuators[ind].units)
                                      for ind in range(len(positions))
                                  ],
                                  mode='abs')
        self.modules_manager.connect_actuators(True)
        self.modules_manager.move_actuators(dte_act, polling=True)
        self.modules_manager.connect_actuators(False)


    def quit(self):
        self.dockarea.parent().close()
        self.clean_h5_temp()

    def set_model(self):
        model_name = self.settings.child('models', 'model_class').value()
        self.model_class = utils.find_dict_in_list_from_key_val(
            MODELS, 'name', model_name)['class'](self)
        self.model_class.ini_model_base()

    def ini_temp_file(self):
        self.clean_h5_temp()

        self.h5temp = H5Saver()
        self.temp_path = tempfile.TemporaryDirectory(prefix='pymo')
        addhoc_file_path = Path(self.temp_path.name).joinpath('bayesian_temp_data.h5')
        self.h5temp.init_file(custom_naming=True, addhoc_file_path=addhoc_file_path)
        act_names = [child.name() for child in self.settings.child( 'main_settings',
                                                                    'bounds').children()]
        act_units = [self.modules_manager.get_mod_from_name(act_name, 'act').units for act_name
                     in act_names]
        self.enlargeable_saver = DataEnlargeableSaver(
            self.h5temp,
            enl_axis_names=act_names,
            enl_axis_units=act_units)

    def ini_live_plot(self):
        self.live_plotter.h5saver = self.h5temp
        act_names = [child.name() for child in self.settings.child('main_settings',
                                                                   'bounds').children()]
        act_units = [self.modules_manager.get_mod_from_name(act_name, 'act').units for act_name
                     in act_names]
        if len(act_names) == 1:
            viewer_enum = 'Viewer1D'
        elif len(act_names) == 2:
            viewer_enum = 'Viewer2D'
        else:
            viewer_enum = 'ViewerND'
        viewers = self.live_plotter.prepare_viewers([viewer_enum],
                                                    viewers_name=[self.explored_viewer_name])
        for viewer in viewers:
            if viewer.has_action('crosshair'):
                viewer.get_action('crosshair').trigger()
                if hasattr(viewer.view, 'collapse_lineout_widgets'):
                    viewer.view.collapse_lineout_widgets()
            if viewer.has_action('sort'):
                if not viewer.is_action_checked('sort'):
                   viewer.get_action('sort').trigger()
            if viewer.has_action('scatter'):
                if not viewer.is_action_checked('scatter'):
                    viewer.get_action('scatter').trigger()
            if viewer.has_action('autolevels'):
                if viewer.is_action_checked('autolevels'):
                    viewer.get_action('autolevels').trigger()
                    viewer.get_action('autolevels').trigger()
            if viewer.has_action('aspect_ratio'):
                if viewer.is_action_checked('aspect_ratio'):
                    viewer.get_action('aspect_ratio').trigger()

        QtWidgets.QApplication.processEvents()
        win_width = self.dockarea.width()
        self.docks['settings'].container().parent().setSizes((int(win_width / 5),
                                                     int(2 * win_width / 5),
                                                     int(2 * win_width / 5), 10, 10))

    def update_actuators(self, actuators: List[str]):
        if self.is_action_checked(OptimizerAction.INI_RUNNER):
            self.get_action(OptimizerAction.INI_RUNNER).trigger()
            QtWidgets.QApplication.processEvents()

        self._save_main_settings = False

        for child in self.settings.child('main_settings', 'bounds').children():
            self.settings.child('main_settings', 'bounds').removeChild(child)
        params = []
        for actuator in actuators:
            params.append({'title': actuator, 'name': actuator, 'type': 'group', 'children': [
                {'title': 'min', 'name': 'min', 'type': 'float',
                 'value': config('optimizer', 'bounds', 'actuator_min')},
                {'title': 'max', 'name': 'max', 'type': 'float',
                 'value': config('optimizer', 'bounds','actuator_max')},
            ]})
        self.settings.child('main_settings', 'bounds').addChildren(params)

        try:
            self.mainsettings_saver_loader.base_path = [self.model_class.__class__.__name__] + \
                                                       self.modules_manager.selected_actuators_name
            self.mainsettings_saver_loader.load_config()
            self._save_main_settings = True
        except Exception as e:
            logger.exception(f'Could not load the configuration')

        self.update_after_actuators_changed(self.modules_manager.selected_actuators_name)

    @abc.abstractmethod
    def update_after_actuators_changed(self, actuators: list[str]):
        """ Actions to do after the actuators have been updated

        To be implemented
        """
        ...

    def format_bounds(self):
        bound_dict = OrderedDict([])
        for bound in self.settings.child('main_settings', 'bounds').children():
            bound_dict.update({bound.name(): (bound['min'], bound['max'])})
        return bound_dict

    @abc.abstractmethod
    def set_algorithm(self):
        self.algorithm = ...

    def ini_model(self):
        try:
            if self.model_class is None:
                self.set_model()

            self.modules_manager.selected_actuators_name = self.model_class.actuators_name
            self.modules_manager.selected_detectors_name = self.model_class.detectors_name

            self.enable_controls_opti(True)
            self.get_action('model_led').set_as_true()
            self.set_action_enabled(OptimizerAction.INI_MODEL, False)
            self.set_action_enabled(OptimizerAction.MODELS, False)

            if self.DISPLAY_BEST:
                self.viewer_observable.update_viewers(['Viewer0D'] + ['Viewer0D' for _ in self.modules_manager.selected_actuators_name],
                                                      ['Fitness'] + [act for act in self.modules_manager.selected_actuators_name])
            self.settings.child('models', 'ini_model').setValue(True)
            self.settings.child('models', 'ini_runner').setOpts(enabled=True)
            self.set_action_enabled(OptimizerAction.INI_RUNNER, True)

            self.mainsettings_saver_loader.base_path = [self.model_class.__class__.__name__] + \
                self.modules_manager.selected_actuators_name
            self.mainsettings_saver_loader.load_config()

            self.modules_manager.settings_tree.setEnabled(True)
            self.settings.child('models', 'ini_model').hide()

            #Warning the activate method here is blocking???
            # try:  # this is correct for Default Model and probably for all models...
            #     self.model_class.settings.child('optimizing_signal', 'data_probe').activate()
            # except Exception:
            #     pass

        except Exception as e:
            logger.exception(str(e))

    def do_save(self):
        """ Properly prepare the extension for saving """
        if self.is_action_checked(OptimizerAction.SAVE):
            if self.is_action_checked(OptimizerAction.INI_RUNNER):
                if self.is_action_checked(OptimizerAction.RUN):
                    self.get_action(OptimizerAction.RUN).trigger()
                    QtWidgets.QApplication.processEvents()
                self.get_action(OptimizerAction.INI_RUNNER).trigger()  # for the model/algo de-initialization to correctly resave data
                # afterwards
                QtWidgets.QApplication.processEvents()
                self.get_action(OptimizerAction.INI_RUNNER).trigger()

    def ini_saver(self):
        if self.is_action_checked(OptimizerAction.SAVE):
            self.module_and_data_saver = module_saving.OptimizerSaver(
                self, enl_axis_names=self.modules_manager.selected_actuators_name,
                enl_axis_units=[act.units for act in self.modules_manager.actuators])
            self.create_new_file(True)
            self.module_and_data_saver.h5saver = self.h5saver
            self.check_create_save_node()
        else:
            self.module_and_data_saver.forget_h5()
            self.module_and_data_saver.h5saver.close_file()

    def recursive_enable(self, param: putils.Parameter, enable=True):
        param.setOpts(enabled=enable)
        for child in param.children():
            self.recursive_enable(child, enable)

    def enable_settings_run(self, enable=True):
        self.modules_manager.settings_tree.setEnabled(enable)
        self.recursive_enable(self.settings.child('models'), enable)
        self.recursive_enable(self.settings.child('main_settings', 'bounds'), enable)
        self.recursive_enable(self.settings.child('main_settings', 'ini_random'), enable)

    def stop_algo(self):
        self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.STOP))

    def restart_algo(self):

        if self.is_action_checked(OptimizerAction.RUN):
            self.get_action(OptimizerAction.RUN).trigger()
            QtWidgets.QApplication.processEvents()

        self.set_algorithm()
        self.model_class.runner_initialized()
        self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.RESTART, self.algorithm))
        self.update_prediction_function()
        if self.viewer_observable is not None:
            for viewer in self.viewer_observable.viewers:
                if isinstance(viewer, Viewer0D):
                    viewer.view.data_displayer.clear_data()

        self.enl_index = 0
        self._optimizing_done_LED.set_as_false()
        self.ini_temp_file()
        self.ini_live_plot()

        if self.is_action_checked(OptimizerAction.SAVE):
            self.check_create_save_node()

        self.get_action(OptimizerAction.RUN).trigger()

    def check_create_save_node(self):
        node_is_empty = (
            len(self.module_and_data_saver.get_set_node().children()) == 0 or
            len(self.module_and_data_saver.get_set_node().get_child('Detector000').children()) == 0)
        node = self.module_and_data_saver.get_set_node(new= not node_is_empty)
        self.h5saver.settings.child('current_scan_name').setValue(node.name)

    def ini_optimization_runner(self):
        self._status_message_label.setText('Initializing Algorithm and thread')
        if self.is_action_checked(OptimizerAction.INI_RUNNER):
            self._optimizing_done_LED.set_as_false()
            if not self.model_class.has_fitness_observable():
                messagebox(title='Warning', text='No 0D observable has been chosen as a fitness value for the algorithm')
                self.set_action_checked(OptimizerAction.INI_RUNNER, False)
                return

            self.enable_settings_run(False)
            if not self._ini_runner:
                self._ini_runner = True
                self.set_algorithm()

                if self.is_action_checked(OptimizerAction.SAVE):
                    self.ini_saver()
                    self.check_create_save_node()

                self.settings.child('models', 'ini_runner').setValue(True)
                self.enl_index = 0

                self.ini_temp_file()
                self.ini_live_plot()

                self.runner_thread = QtCore.QThread()
                runner = self.runner(self.model_class, self.modules_manager, self.algorithm,
                                     self.get_stopping_parameters())
                self.runner_thread.runner = runner
                runner.algo_live_plot_signal.connect(self.do_live_plot)
                runner.algo_finished.connect(self.optimization_done)
                runner.runner_command.connect(self.thread_status)
                runner.saver_signal.connect(self.add_data)
                self.command_runner.connect(runner.queue_command)

                runner.moveToThread(self.runner_thread)
                self.runner_thread.start()
                self.get_action('runner_led').set_as_true()
                self.set_action_enabled(OptimizerAction.RUN, True)
                self.set_action_enabled(OptimizerAction.RESTART, True)
                self.set_action_enabled(OptimizerAction.STOP, True)
                self.model_class.runner_initialized()
                self.update_prediction_function()
        else:
            self.set_action_enabled(OptimizerAction.INI_RUNNER, False)
            self.enable_settings_run(True)
            if self.is_action_checked(OptimizerAction.RUN):
                self.get_action(OptimizerAction.RUN).trigger()
                QtWidgets.QApplication.processEvents()

            self._status_message_label.setText('Quitting Runner Thread')
            try:
                self.command_runner.disconnect()
            except TypeError:
                pass
            if self.runner_thread is not None:
                self.runner_thread.quit()
                self.runner_thread.wait(5000)
                if not self.runner_thread.isFinished():
                    self.runner_thread.terminate()
                    self.runner_thread.wait()
            self.splash.setVisible(False)
            self.get_action('runner_led').set_as_false()
            self._ini_runner = False
            self.set_action_enabled(OptimizerAction.RUN, False)
            self.set_action_enabled(OptimizerAction.RESTART, False)
            self.set_action_enabled(OptimizerAction.STOP, False)
            self.set_action_enabled(OptimizerAction.INI_RUNNER, True)  # reactivate the action only when the thread is finished

    def clean_h5_temp(self):
        if self.temp_path is not None:
            try:
                self.h5temp.close()
                self.temp_path.cleanup()
            except Exception as e:
                logger.exception(str(e))

    def optimization_done(self, dte: DataToExport):
        self.go_to_best()
        self.get_action(OptimizerAction.RUN).trigger()
        self.optimization_done_signal.emit(dte)
        self._optimizing_done_LED.set_as_true()
        self._status_message_label.setText('Optimization Done')

    def do_live_plot(self, dte_algo: DataToExport):
        self.enl_index += 1
        self._optimizing_step.setValue(self.enl_index)
        self.model_class.update_plots()

        dwa_data = dte_algo.pop(dte_algo.index_from_name_origin(DataNames.ProbedData, 'algo'))

        actuators_values = [
            dte_algo.get_data_from_name_origin(
                act,
                DataNames.Actuators)
            .value() for act in self.modules_manager.selected_actuators_name]

        best_individual = [
            dte_algo.get_data_from_name_origin(
                act,
                DataNames.Individual)
            .value() for act in self.modules_manager.selected_actuators_name]

        fitness = dte_algo.get_data_from_name('fitness')

        dte_live = DataToExport('Live', data=[
            DataCalculated('Fitness',
                           data=[np.atleast_1d(dwa_data.value()), np.atleast_1d(fitness.value())],
                           labels=['Fitness', 'Fitness_best']
                           ),])
        for ind, act in enumerate(self.modules_manager.actuators):
            dte_live.append([
                DataCalculated(act.title,
                               data=[np.atleast_1d(actuators_values[ind]),
                                     np.atleast_1d(best_individual[ind])],
                               labels=[act.title, f'{act.title}_best'],
                               units=act.units
                           ),
                                ])

        if self.DISPLAY_BEST:
            self.viewer_observable.show_data(dte_live)


        self.enlargeable_saver.add_data('/RawData', dwa_data,
                                        axis_values=actuators_values)
        if len(best_individual) == 1 or (
                len(best_individual) == 2 and self.enl_index >= 3):
            self.update_data_plot(target_at=actuators_values,
                                  crosshair_at=best_individual)

    def update_data_plot(self, target_at=None, crosshair_at=None):
        self.live_plotter.load_plot_data(remove_navigation=False,
                                         crosshair_at=crosshair_at,
                                         target_at=target_at)

    def enable_controls_opti(self, enable: bool):
        pass

    def run_optimization(self):
        if self.is_action_checked(OptimizerAction.RUN):
            self._status_message_label.setText('Running Optimization')
            self.set_action_enabled(OptimizerAction.SAVE, False)
            self.get_action(OptimizerAction.RUN).set_icon('pause')
            self.set_action_enabled(OptimizerAction.GO_TO_BEST, False)
            self.set_action_checked(OptimizerAction.GO_TO, False)
            self.set_action_enabled(OptimizerAction.GO_TO, False)
            self.set_action_enabled(OptimizerAction.INI_RUNNER, False)
            self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.START))
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
            self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.RUN))
        else:
            self._status_message_label.setText('Pausing Optimization')
            self.get_action(OptimizerAction.RUN).set_icon('run2')
            self.set_action_enabled(OptimizerAction.SAVE, True)
            self.command_runner.emit(utils.ThreadCommand(OptimizerToRunner.PAUSE))
            self.set_action_enabled(OptimizerAction.GO_TO_BEST, True)
            self.set_action_enabled(OptimizerAction.GO_TO, True)
            self.set_action_enabled(OptimizerAction.INI_RUNNER, True)
            QtWidgets.QApplication.processEvents()

    def thread_status(self, status: utils.ThreadCommand):
        """To reimplement if needed"""




