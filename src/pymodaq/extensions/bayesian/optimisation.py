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
                                               BayesianAlgorithm)
from pymodaq.utils.gui_utils import QLED
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.h5modules.data_saving import DataEnlargeableSaver
from pymodaq.post_treatment.load_and_plot import LoaderPlotter


logger = utils.set_logger(utils.get_module_name(__file__))

EXTENSION_NAME = 'BayesianOptimisation'
CLASS_NAME = 'BayesianOptimisation'


class BayesianOptimisation(gutils.CustomApp):
    command_runner = QtCore.Signal(utils.ThreadCommand)
    models = get_bayesian_models()

    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': True, 'type': 'group',
         'children': [{'title': 'Ini. State', 'name': 'ini_random', 'type': 'int', 'value': 5},
                      {'title': 'bounds', 'name': 'bounds', 'type': 'group', 'children': []}]},

        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True,
         'children': [
            {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
             'limits': [d['name'] for d in models]},
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
        self._modules_manager = ModulesManager(self.dashboard.detector_modules,
                                               self.dashboard.actuators_modules)
        self.modules_manager.actuators_changed[list].connect(self.update_actuators)
        self.modules_manager.settings.child('data_dimensions').setOpts(expanded=False)
        self.modules_manager.settings.child('actuators_positions').setOpts(expanded=False)
        self.setup_ui()

        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None

        self.enlargeable_saver: DataEnlargeableSaver = None
        self.live_plotter = LoaderPlotter(self.dockarea)

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
        self.docks['settings'].addWidget(self.modules_manager.settings_tree)
        self.docks['settings'].addWidget(self.settings_tree)

        widget_observable = QtWidgets.QWidget()
        widget_observable.setLayout(QtWidgets.QHBoxLayout())
        observable_dockarea = gutils.DockArea()
        widget_observable.layout().addWidget(observable_dockarea)
        self.viewer_observable = ViewerDispatcher(observable_dockarea)
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

    def setup_actions(self):
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.add_action('ini_model', 'Init Model', 'ini')
        self.add_widget('model_led', QLED, toolbar=self.toolbar)
        self.add_action('ini_runner', 'Init the Optimisation Algorithm', 'ini', checkable=True)
        self.add_widget('runner_led', QLED, toolbar=self.toolbar)
        self.add_action('run', 'Run Optimisation', 'run2', checkable=True)
        self.add_action('pause', 'Pause Optimisation', 'pause', checkable=True)
        logger.debug('actions set')

    def connect_things(self):
        logger.debug('connecting things')
        self.connect_action('quit', self.quit, )
        self.connect_action('ini_model', self.ini_model)
        self.connect_action('ini_runner', self.ini_optimisation_runner)
        self.connect_action('run', self.run_optimisation)
        self.connect_action('pause', self.pause_runner)
        self.modules_manager

    def pause_runner(self):
        self.command_runner.emit(utils.ThreadCommand('pause_PID', self.is_action_checked('pause')))

    def quit(self):
        self.dockarea.parent().close()

    def set_model(self):
        model_name = self.settings.child('models', 'model_class').value()
        self.model_class = utils.find_dict_in_list_from_key_val(self.models,
                                                                'name',
                                                                model_name)['class'](self)
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

        self.live_plotter.h5saver = self.h5temp
        self.live_plotter.prepare_viewers(['ViewerND'],
                                          viewers_name=['algo/ProbedData'])

    def update_actuators(self, actuators: List[str]):
        if self.is_action_checked('ini_runner'):
            self.get_action('ini_runner').trigger()
            QtWidgets.QApplication.processEvents()

        for child in self.settings.child('main_settings', 'bounds').children():
            self.settings.child('main_settings', 'bounds').removeChild(child)
        params = []
        for actuator in actuators:
            params.append({'title': actuator, 'name': actuator, 'type': 'group', 'children': [
                {'title': 'min', 'name': 'min', 'type': 'float', 'value': -5},
                {'title': 'max', 'name': 'max', 'type': 'float', 'value': 5},
            ]})
        self.settings.child('main_settings', 'bounds').addChildren(params)

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

        except Exception as e:
            logger.exception(str(e))

    def ini_optimisation_runner(self):
        if self.is_action_checked('ini_runner'):
            self.set_algorithm()

            self.ini_temp_file()

            self.runner_thread = QtCore.QThread()
            runner = OptimisationRunner(self.model_class, self.modules_manager, self.algorithm)
            self.runner_thread.runner = runner
            runner.algo_output_signal.connect(self.process_output)
            self.command_runner.connect(runner.queue_command)

            runner.moveToThread(self.runner_thread)

            self.runner_thread.start()
            self.get_action('runner_led').set_as_true()

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

    def process_output(self, dte: DataToExport):
        dwa_data = dte.remove(dte.get_data_from_name('ProbedData'))
        dwa_actuators = dte.remove(dte.get_data_from_name('Actuators'))

        self.viewer_observable.show_data(dte)
        self.enlargeable_saver.add_data('/RawData', dwa_data,
                                        axis_values=dwa_actuators.values())

        self.update_data_plot()

    def update_data_plot(self):
        self.live_plotter.load_plot_data(remove_navigation=False)

    def enable_controls_opti(self, enable: bool):
        pass

    def run_optimisation(self):
        if self.is_action_checked('run'):
            self.get_action('run').set_icon('stop')
            self.command_runner.emit(utils.ThreadCommand('start', {}))
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
            self.command_runner.emit(utils.ThreadCommand('run', {}))
        else:
            self.get_action('run').set_icon('run2')
            self.command_runner.emit(utils.ThreadCommand('stop', {}))

            QtWidgets.QApplication.processEvents()


class OptimisationRunner(QtCore.QObject):
    algo_output_signal = QtCore.Signal(DataToExport)

    def __init__(self, model_class: BayesianModelGeneric, modules_manager: ModulesManager,
                 algorithm: BayesianAlgorithm):
        super().__init__()

        self.det_done_datas: DataToExport = None
        self.input_from_dets: float = None
        self.outputs: List[np.ndarray] = []
        self.dte_actuators: DataToExport = None

        self.model_class: BayesianModelGeneric = model_class
        self.modules_manager: ModulesManager = modules_manager

        self.running = True
        self.paused = False

        self.optimisation_algorithm: BayesianAlgorithm = algorithm

    @QtCore.Slot(utils.ThreadCommand)
    def queue_command(self, command: utils.ThreadCommand):
        """
        """
        if command.command == "run":
            self.run_opti(**command.attribute)

        elif command.command == "pause":
            self.pause_opti(command.attribute)

        elif command.command == "stop":
            self.running = False

    def pause_opti(self, pause_state: bool):
        self.paused = pause_state

    def run_opti(self, sync_detectors=True, sync_acts=False):
        """Start the optimisation loop

        Parameters
        ----------
        sync_detectors: (bool) if True will make sure all selected detectors (if any) all got their data before calling
            the model
        sync_acts: (bool) if True will make sure all selected actuators (if any) all reached their target position
         before calling the model
        """
        self.running = True
        try:
            if sync_detectors:
                self.modules_manager.connect_detectors()
            if sync_acts:
                self.modules_manager.connect_actuators()

            self.current_time = time.perf_counter()
            logger.info('Optimisation loop starting')
            while self.running:
                if not self.paused:
                    next_target = self.optimisation_algorithm.ask()

                    self.outputs = next_target
                    self.output_to_actuators: DataToActuators =\
                        self.model_class.convert_output(self.outputs)

                    self.modules_manager.move_actuators(self.output_to_actuators,
                                                        self.output_to_actuators.mode,
                                                        polling=False)

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
                                                                                 'Actuators')
                                             ])
                    self.algo_output_signal.emit(dte)

                self.current_time = time.perf_counter()
                QtWidgets.QApplication.processEvents()


            logger.info('Optimisation loop exiting')
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

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
    file = Path(get_set_preset_path()).joinpath(f"{'complex_data'}.xml")
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
