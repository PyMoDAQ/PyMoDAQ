from typing import List, Union, Optional
import tempfile
from pathlib import Path

from qtpy import QtWidgets, QtCore
import time
import numpy as np


from pymodaq.utils.data import DataToExport, DataToActuators, DataCalculated, DataActuator
from pymodaq.utils.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq.utils.plotting.data_viewers.viewer import ViewerDispatcher, ViewersEnum
from pymodaq.extensions.bayesian.utils import (get_bayesian_models, BayesianModelGeneric,
                                               BayesianAlgorithm, UtilityKind,
                                               UtilityParameters, StopType, StoppingParameters)
from pymodaq.utils.gui_utils import QLED
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.h5modules.data_saving import DataEnlargeableSaver
from pymodaq.post_treatment.load_and_plot import LoaderPlotter
from pymodaq.extensions.bayesian.utils import BayesianConfig
from pymodaq.utils import config as configmod
from pymodaq.utils.logger import set_logger, get_module_name


EXTENSION_NAME = 'BayesianOptimisation'
CLASS_NAME = 'BayesianOptimisation'

logger = set_logger(get_module_name(__file__))


class BayesianOptimisation(gutils.CustomApp):
    """ PyMoDAQ extension of the DashBoard to perform the optimization of a target signal
    taken form the detectors as a function of one or more parameters controlled by the actuators.
    """

    command_runner = QtCore.Signal(utils.ThreadCommand)
    models = get_bayesian_models()
    explored_viewer_name = 'algo/ProbedData'
    optimisation_done_signal = QtCore.Signal(DataToExport)

    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': True, 'type': 'group',
         'children': [
             {'title': 'Utility Function:', 'name': 'utility', 'expanded': False, 'type': 'group',
              'children': [
                  {'title': 'Kind', 'name': 'kind', 'type': 'list',
                   'limits': UtilityKind.to_dict_value()},
                  {'title': 'Kappa:', 'name': 'kappa', 'type': 'slide', 'value': 2.576,
                   'min': 0.001, 'max': 100, 'subtype': 'log',
                   'tip': 'Parameter to indicate how closed are the next parameters sampled.'
                          'Higher value = favors spaces that are least explored.'
                          'Lower value = favors spaces where the regression function is the '
                          'highest.'},
                  {'title': 'Kappa actual:', 'name': 'kappa_actual', 'type': 'float', 'value': 2.576,
                   'tip': 'Current value of the kappa parameter', 'readonly': True},
                  {'title': 'xi:', 'name': 'xi', 'type': 'slide', 'value': 0,
                   'tip': 'Governs the exploration/exploitation tradeoff.'
                          'Lower prefers exploitation, higher prefers exploration.'},
                  {'title': 'Kappa decay:', 'name': 'kappa_decay', 'type': 'float', 'value': 0.9,
                   'tip': 'kappa is multiplied by this factor every iteration.'},
                  {'title': 'Kappa decay delay:', 'name': 'kappa_decay_delay', 'type': 'int',
                   'value': 20, 'tip': 'Number of iterations that must have passed before applying '
                                      'the decay to kappa.'},
              ]},
             {'title': 'Stopping Criteria:', 'name': 'stopping', 'expanded': False, 'type': 'group',
              'children': [
                  {'title': 'Niteration', 'name': 'niter', 'type': 'int', 'value': 100, 'min': -1},
                  {'title': 'Type:', 'name': 'stop_type', 'type': 'list',
                   'limits': StopType.names()},
                  {'title': 'Tolerance', 'name': 'tolerance', 'type': 'slide', 'value': 1e-2,
                   'min': 1e-8, 'max': 1, 'subtype': 'log',},
                  {'title': 'Npoints', 'name': 'npoints', 'type': 'int', 'value': 5, 'min': 1},
              ]},
             {'title': 'Ini. State', 'name': 'ini_random', 'type': 'int', 'value': 5},
             {'title': 'bounds', 'name': 'bounds', 'type': 'group', 'children': []},
         ]},

        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True,
         'children': [
            {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
             'limits': [d['name'] for d in models]},
            {'title': 'Ini Model', 'name': 'ini_model', 'type': 'action', },
            {'title': 'Ini Algo', 'name': 'ini_runner', 'type': 'action', 'enabled': False},
            {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},
        ]},
        {'title': 'Move settings:', 'name': 'move_settings', 'expanded': True, 'type': 'group',
         'visible': False, 'children': [
             {'title': 'Units:', 'name': 'units', 'type': 'str', 'value': ''}]},

    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        self.algorithm: Optional[BayesianAlgorithm] = None
        self.viewer_fitness: Optional[Viewer0D] = None
        self.viewer_observable: Optional[ViewerDispatcher] = None
        self.model_class: Optional[BayesianModelGeneric] = None
        self._save_main_settings = True
        self._modules_manager = ModulesManager(self.dashboard.detector_modules,
                                               self.dashboard.actuators_modules)
        self.modules_manager.actuators_changed[list].connect(self.update_actuators)
        self.modules_manager.settings.child('data_dimensions').setOpts(expanded=False)
        self.modules_manager.settings.child('actuators_positions').setOpts(expanded=False)
        self.setup_ui()

        self.bayesian_config = BayesianConfig()
        self.mainsettings_saver_loader = configmod.ConfigSaverLoader(
            self.settings.child('main_settings'), self.bayesian_config)

        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None

        self.enlargeable_saver: DataEnlargeableSaver = None
        self.live_plotter = LoaderPlotter(self.dockarea)

        self.enl_index = 0

        self.settings.child('models', 'ini_model').sigActivated.connect(
            self.get_action('ini_model').trigger)

        self.settings.child('models', 'ini_runner').sigActivated.connect(
            self.get_action('ini_runner').trigger)

    @property
    def modules_manager(self) -> ModulesManager:
        return self._modules_manager

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
        self.docks['settings'] = gutils.Dock('Settings')
        self.dockarea.addDock(self.docks['settings'])
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.docks['settings'].addWidget(splitter)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.modules_manager.settings_tree)
        self.modules_manager.show_only_control_modules(False)
        splitter.setSizes((int(self.dockarea.height() / 2),
                           int(self.dockarea.height() / 2)))

        widget_observable = QtWidgets.QWidget()
        widget_observable.setLayout(QtWidgets.QHBoxLayout())
        observable_dockarea = gutils.DockArea()
        widget_observable.layout().addWidget(observable_dockarea)
        self.viewer_observable = ViewerDispatcher(observable_dockarea, direction='bottom')
        self.docks['observable'] = gutils.Dock('Observable')
        self.dockarea.addDock(self.docks['observable'], 'right', self.docks['settings'])
        self.docks['observable'].addWidget(widget_observable)

        if len(self.models) != 0:
            self.get_set_model_params(self.models[0]['name'])

    def get_set_model_params(self, model_name):
        self.settings.child('models', 'model_params').clearChildren()
        if len(self.models) > 0:
            model_class = utils.find_dict_in_list_from_key_val(self.models, 'name', model_name)['class']
            params = getattr(model_class, 'params')
            self.settings.child('models', 'model_params').addChildren(params)

    def setup_menu(self):
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
        elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
            if self.model_class is not None:
                self.model_class.update_settings(param)
        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'utility'), []):
            if param.name() != 'kappa_actual':
                self.update_utility_function()
        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'bounds'), []):
            self.update_bounds()
        elif param.name() in putils.iter_children(
            self.settings.child('main_settings', 'stopping'), []):
            self.update_stopping_criteria()
        if self._save_main_settings and param.name() in putils.iter_children(
                self.settings.child('main_settings'), []):
            self.mainsettings_saver_loader.save_config()

    def update_utility_function(self):
        utility_settings = self.settings.child('main_settings', 'utility')
        uparams = UtilityParameters(utility_settings['kind'], utility_settings['kappa'],
                                    utility_settings['xi'], utility_settings['kappa_decay'],
                                    utility_settings['kappa_decay_delay'])
        self.command_runner.emit(utils.ThreadCommand('utility', uparams))

    def get_stopping_parameters(self) -> StoppingParameters:
        stopping_settings = self.settings.child('main_settings', 'stopping')
        stopping_params = StoppingParameters(stopping_settings['niter'],
                                             stopping_settings['stop_type'],
                                             stopping_settings['tolerance'],
                                             stopping_settings['npoints'])
        return stopping_params

    def update_stopping_criteria(self):
        self.command_runner.emit(utils.ThreadCommand('stopping', self.get_stopping_parameters()))

    def update_bounds(self):
        bounds = {}
        for child in self.settings.child('main_settings', 'bounds').children():
            bounds[child.name()] = (child['min'], child['max'])

        self.command_runner.emit(utils.ThreadCommand('bounds', bounds))

    def setup_actions(self):
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.add_action('ini_model', 'Init Model', 'ini')
        self.add_widget('model_led', QLED, toolbar=self.toolbar)
        self.add_action('ini_runner', 'Init the Optimisation Algorithm', 'ini', checkable=True,
                        enabled=False)
        self.add_widget('runner_led', QLED, toolbar=self.toolbar)
        self.add_action('run', 'Run Optimisation', 'run2', checkable=True, enabled=False)
        self.add_action('gotobest', 'Got to best individual', 'move_contour', enabled=False,
                        tip='Go to the best individual guessed by the algorithm')
        logger.debug('actions set')

    def connect_things(self):
        logger.debug('connecting things')
        self.connect_action('quit', self.quit, )
        self.connect_action('ini_model', self.ini_model)
        self.connect_action('ini_runner', self.ini_optimisation_runner)
        self.connect_action('run', self.run_optimisation)
        self.connect_action('gotobest', self.go_to_best)

    def go_to_best(self):
        best_individual = self.algorithm.best_individual
        actuators = self.modules_manager.selected_actuators_name
        dte_act = DataToActuators('best', data=[
            DataActuator(actuators[ind], data=float(best_individual[ind])) for ind in range(len(best_individual))
        ],
                                  mode='abs')
        self.modules_manager.connect_actuators(True)
        self.modules_manager.move_actuators(dte_act, polling=True)
        self.modules_manager.connect_actuators(False)

        self.modules_manager.grab_datas()

    def quit(self):
        self.dockarea.parent().close()
        self.clean_h5_temp()

    def set_model(self):
        model_name = self.settings.child('models', 'model_class').value()
        self.model_class = utils.find_dict_in_list_from_key_val(
            self.models, 'name', model_name)['class'](self)
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

        QtWidgets.QApplication.processEvents()
        win_width = self.dockarea.width()
        self.docks['settings'].container().setSizes((int(win_width / 5),
                                                     int(2 * win_width / 5),
                                                     int(2 * win_width / 5), 10, 10))

    def update_actuators(self, actuators: List[str]):
        if self.is_action_checked('ini_runner'):
            self.get_action('ini_runner').trigger()
            QtWidgets.QApplication.processEvents()

        self._save_main_settings = False

        for child in self.settings.child('main_settings', 'bounds').children():
            self.settings.child('main_settings', 'bounds').removeChild(child)
        params = []
        for actuator in actuators:
            params.append({'title': actuator, 'name': actuator, 'type': 'group', 'children': [
                {'title': 'min', 'name': 'min', 'type': 'float', 'value': -5},
                {'title': 'max', 'name': 'max', 'type': 'float', 'value': 5},
            ]})
        self.settings.child('main_settings', 'bounds').addChildren(params)
        self.mainsettings_saver_loader.base_path = [self.model_class.__class__.__name__] + \
            self.modules_manager.selected_actuators_name
        self.mainsettings_saver_loader.load_config()
        self._save_main_settings = True

    def format_bounds(self):
        bound_dict = {}
        for bound in self.settings.child('main_settings', 'bounds').children():
            bound_dict.update({bound.name(): (bound['min'], bound['max'])})
        return bound_dict

    def set_algorithm(self):
        self.algorithm = BayesianAlgorithm(
            ini_random=self.settings['main_settings', 'ini_random'],
            bounds=self.format_bounds(),)

    def ini_model(self):
        try:
            if self.model_class is None:
                self.set_model()

            self.modules_manager.selected_actuators_name = self.model_class.actuators_name
            self.modules_manager.selected_detectors_name = self.model_class.detectors_name

            self.enable_controls_opti(True)
            self.get_action('model_led').set_as_true()
            self.set_action_enabled('ini_model', False)

            self.viewer_observable.update_viewers(['Viewer0D', 'Viewer0D'],
                                                  ['Fitness', 'Individual'])
            self.settings.child('models', 'ini_model').setValue(True)
            self.settings.child('models', 'ini_runner').setOpts(enabled=True)
            self.set_action_enabled('ini_runner', True)

            self.mainsettings_saver_loader.base_path = [self.model_class.__class__.__name__] + \
                self.modules_manager.selected_actuators_name
            self.mainsettings_saver_loader.load_config()

            try:  # this is correct for Default Model and probably for all models...
                self.model_class.settings.child('optimizing_signal', 'data_probe').activate()
            except Exception:
                pass

        except Exception as e:
            logger.exception(str(e))

    def ini_optimisation_runner(self):
        if self.is_action_checked('ini_runner'):
            self.set_algorithm()

            self.settings.child('models', 'ini_runner').setValue(True)
            self.enl_index = 0

            self.ini_temp_file()
            self.ini_live_plot()

            self.runner_thread = QtCore.QThread()
            runner = OptimisationRunner(self.model_class, self.modules_manager, self.algorithm,
                                        self.get_stopping_parameters())
            self.runner_thread.runner = runner
            runner.algo_output_signal.connect(self.process_output)
            runner.algo_finished.connect(self.optimisation_done)
            self.command_runner.connect(runner.queue_command)

            runner.moveToThread(self.runner_thread)

            self.runner_thread.start()
            self.get_action('runner_led').set_as_true()
            self.set_action_enabled('run', True)
            self.model_class.runner_initialized()
            self.update_utility_function()
        else:
            if self.is_action_checked('run'):
                self.get_action('run').trigger()
                QtWidgets.QApplication.processEvents()
            self.runner_thread.terminate()
            self.get_action('runner_led').set_as_false()

    def clean_h5_temp(self):
        if self.temp_path is not None:
            try:
                self.h5temp.close()
                self.temp_path.cleanup()
            except Exception as e:
                logger.exception(str(e))

    def optimisation_done(self, dte: DataToExport):
        self.go_to_best()
        self.optimisation_done_signal.emit(dte)

    def process_output(self, dte: DataToExport):

        self.enl_index += 1
        dwa_kappa = dte.remove(dte.get_data_from_name('kappa'))
        self.settings.child('main_settings', 'utility', 'kappa_actual').setValue(
            float(dwa_kappa[0][0])
        )

        dwa_data = dte.remove(dte.get_data_from_name('ProbedData'))
        dwa_actuators: DataActuator = dte.remove(dte.get_data_from_name('Actuators'))
        self.viewer_observable.show_data(dte)

        # dwa_observations = self.algorithm.get_dwa_obervations(
        #     self.modules_manager.selected_actuators_name)
        self.model_class.update_plots()

        best_individual = dte.get_data_from_name('Individual')
        best_indiv_as_list = [float(best_individual[ind][0]) for ind in range(len(best_individual))]


        self.enlargeable_saver.add_data('/RawData', dwa_data,
                                        axis_values=dwa_actuators.values())
        if len(best_indiv_as_list) == 1 or (
                len(best_indiv_as_list) == 2 and self.enl_index >= 3):
            self.update_data_plot(target_at=dwa_actuators.values(),
                                  crosshair_at=best_indiv_as_list)

    def update_data_plot(self, target_at=None, crosshair_at=None):
        self.live_plotter.load_plot_data(remove_navigation=False,
                                         crosshair_at=crosshair_at,
                                         target_at=target_at)

    def enable_controls_opti(self, enable: bool):
        pass

    def run_optimisation(self):
        if self.is_action_checked('run'):
            self.get_action('run').set_icon('pause')
            self.command_runner.emit(utils.ThreadCommand('start', {}))
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
            self.command_runner.emit(utils.ThreadCommand('run', {}))
        else:
            self.get_action('run').set_icon('run2')
            self.command_runner.emit(utils.ThreadCommand('stop', {}))
            self.set_action_enabled('gotobest', True)

            QtWidgets.QApplication.processEvents()


class OptimisationRunner(QtCore.QObject):
    algo_output_signal = QtCore.Signal(DataToExport)
    algo_finished = QtCore.Signal(DataToExport)

    def __init__(self, model_class: BayesianModelGeneric, modules_manager: ModulesManager,
                 algorithm: BayesianAlgorithm, stopping_params: StoppingParameters):
        super().__init__()

        self.det_done_datas: DataToExport = None
        self.input_from_dets: float = None
        self.outputs: List[np.ndarray] = []
        self.dte_actuators: DataToExport = None
        self.stopping_params: StoppingParameters = stopping_params

        self.model_class: BayesianModelGeneric = model_class
        self.modules_manager: ModulesManager = modules_manager

        self.running = True

        self.optimisation_algorithm: BayesianAlgorithm = algorithm

        self._ind_iter: int = 0

    @QtCore.Slot(utils.ThreadCommand)
    def queue_command(self, command: utils.ThreadCommand):
        """
        """
        if command.command == "run":
            self.run_opti(**command.attribute)

        elif command.command == "stop":
            self.running = False

        elif command.command == 'utility':
            utility_params: UtilityParameters = command.attribute
            self.optimisation_algorithm.set_utility_function(
                utility_params.kind,
                kappa=utility_params.kappa,
                xi=utility_params.xi,
                kappa_decay=utility_params.kappa_decay,
                kappa_decay_delay=utility_params.kappa_decay_delay)

        elif command.command == 'stopping':
            self.stopping_params: StoppingParameters = command.attribute

        elif command.command == 'bounds':
            self.optimisation_algorithm.set_bounds(command.attribute)

    def run_opti(self, sync_detectors=True, sync_acts=True):
        """Start the optimisation loop

        Parameters
        ----------
        sync_detectors: (bool) if True will make sure all selected detectors (if any) all got their data before calling
            the model
        sync_acts: (bool) if True will make sure all selected actuators (if any) all reached their target position
         before calling the model
        """
        self.running = True
        converged = False
        try:
            if sync_detectors:
                self.modules_manager.connect_detectors()
            if sync_acts:
                self.modules_manager.connect_actuators()

            self.current_time = time.perf_counter()
            logger.info('Optimisation loop starting')
            while self.running:
                self._ind_iter += 1

                next_target = self.optimisation_algorithm.ask()

                self.outputs = next_target
                self.output_to_actuators: DataToActuators =\
                    self.model_class.convert_output(
                        self.outputs,
                        best_individual=self.optimisation_algorithm.best_individual
                    )

                self.modules_manager.move_actuators(self.output_to_actuators,
                                                    self.output_to_actuators.mode,
                                                    polling=sync_acts)

                # Do the evaluation (measurements)
                self.det_done_datas = self.modules_manager.grab_datas()
                self.input_from_dets = self.model_class.convert_input(self.det_done_datas)

                # Run the algo internal mechanic
                self.optimisation_algorithm.tell(float(self.input_from_dets))

                dte = DataToExport('algo',
                                   data=[self.individual_as_data(
                                       np.array([self.optimisation_algorithm.best_fitness]),
                                       'Fitness'),
                                       self.individual_as_data(
                                           self.optimisation_algorithm.best_individual,
                                           'Individual'),
                                       DataCalculated('ProbedData',
                                                      data=[np.array([self.input_from_dets])],
                                                      ),
                                       self.output_to_actuators.merge_as_dwa('Data0D',
                                                                             'Actuators'),
                                       DataCalculated(
                                           'kappa',
                                           data=[
                                               np.array([self.optimisation_algorithm.kappa])])
                                         ])
                self.algo_output_signal.emit(dte)

                self.optimisation_algorithm.update_utility_function()

                if self.optimisation_algorithm.stopping(self._ind_iter, self.stopping_params):
                    converged = True
                    break

            self.current_time = time.perf_counter()
            QtWidgets.QApplication.processEvents()

            logger.info('Optimisation loop exiting')
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

            if converged:
                self.algo_finished.emit(dte)

        except Exception as e:
            logger.exception(str(e))

    @staticmethod
    def individual_as_data(individual: np.ndarray, name: str = 'Individual') -> DataCalculated:
        return DataCalculated(name, data=[np.atleast_1d(np.squeeze(coordinate)) for coordinate in
                                          np.atleast_1d(np.squeeze(individual))])


def main(init_qt=True):
    import sys
    from pathlib import Path
    from pymodaq.utils.daq_utils import get_set_preset_path

    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    from pymodaq.dashboard import DashBoard

    win = QtWidgets.QMainWindow()
    area = gutils.dock.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dashboard = DashBoard(area)
    daq_scan = None
    file = Path(get_set_preset_path()).joinpath(f"{'beam_steering_mock'}.xml")

    if file.exists():
        dashboard.set_preset_mode(file)
        daq_scan = dashboard.load_bayesian()
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQScan Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    if init_qt:
        sys.exit(app.exec_())
    return dashboard, daq_scan, win


if __name__ == '__main__':
    main()

