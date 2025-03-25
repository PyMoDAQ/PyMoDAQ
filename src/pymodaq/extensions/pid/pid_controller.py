import time
from functools import partial  # needed for the button to sync setpoint with currpoint
from typing import Dict, List, TYPE_CHECKING

import numpy as np

from qtpy import QtGui, QtWidgets
from qtpy.QtCore import QObject, Slot, QThread, Signal

from simple_pid import PID

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand, find_dict_in_list_from_key_val
from pymodaq.utils.exceptions import DetectorError, ActuatorError, PIDError

from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_gui.utils.widgets import QLED, LabelWithFont, SpinBox
from pymodaq_gui.utils.dock import DockArea, Dock


from pymodaq_data.data import DataToExport, DataCalculated, DataRaw
from pymodaq_utils.config import Config

from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.extensions.pid.utils import get_models
from pymodaq.utils.data import DataActuator, DataToActuators
from pymodaq.extensions.pid.actuator_controller import PIDController
from pymodaq.extensions.utils import CustomExt

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move


config = Config()
logger = set_logger(get_module_name(__file__))


def convert_output_limits(lim_min=-10., min_status=False, lim_max=10., max_status=False):
    output = [None, None]
    if min_status:
        output[0] = lim_min
    if max_status:
        output[1] = lim_max
    return output


class DAQ_PID(CustomExt):
    """
    """
    command_pid = Signal(ThreadCommand)
    curr_points_signal = Signal(dict)
    setpoints_signal = Signal(dict)
    emit_curr_points_sig = Signal()

    models = get_models()

    params = [
        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True, 'children': [
            {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
             'limits': [d['name'] for d in models]},
            {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},
        ]},
        {'title': 'Move settings:', 'name': 'move_settings', 'expanded': True, 'type': 'group', 'visible': False,
         'children': [
             {'title': 'Units:', 'name': 'units', 'type': 'str', 'value': ''}]},
        # here only to be compatible with DAQ_Scan, the model could update it

        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': True, 'type': 'group', 'children': [
            {'title': 'Acquisition Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000},
            {'title': 'epsilon', 'name': 'epsilon', 'type': 'float', 'value': 0.01,
             'tooltip': 'Precision at which move is considered as done'},
            {'title': 'PID controls:', 'name': 'pid_controls', 'type': 'group', 'children': [
                {'title': 'Sample time (ms):', 'name': 'sample_time', 'type': 'int', 'value': 10},
                {'title': 'Refresh plot time (ms):', 'name': 'refresh_plot_time', 'type': 'int', 'value': 200},
                {'title': 'Output limits:', 'name': 'output_limits', 'expanded': True, 'type': 'group', 'children': [
                    {'title': 'Output limit (min):', 'name': 'output_limit_min_enabled', 'type': 'bool',
                     'value': False},
                    {'title': 'Output limit (min):', 'name': 'output_limit_min', 'type': 'float', 'value': 0},
                    {'title': 'Output limit (max):', 'name': 'output_limit_max_enabled', 'type': 'bool',
                     'value': False},
                    {'title': 'Output limit (max:', 'name': 'output_limit_max', 'type': 'float', 'value': 100},
                ]},
                {'title': 'Auto mode:', 'name': 'auto_mode', 'type': 'bool', 'value': False, 'readonly': True},
                {'title': 'Prop. on measurement:', 'name': 'proportional_on_measurement', 'type': 'bool',
                 'value': False},
                {'title': 'PID constants:', 'name': 'pid_constants', 'type': 'group', 'children': [
                    {'title': 'Kp:', 'name': 'kp', 'type': 'float', 'value': 0.1, 'min': 0},
                    {'title': 'Ki:', 'name': 'ki', 'type': 'float', 'value': 0.01, 'min': 0},
                    {'title': 'Kd:', 'name': 'kd', 'type': 'float', 'value': 0.001, 'min': 0},
                ]},

            ]},

        ]},
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

        self.settings = Parameter.create(title='PID settings', name='pid_settings', type='group', children=self.params)
        self.title = 'PyMoDAQ PID'

        self.initialized_state = False
        self.model_class = None
        self._curr_points = dict([])
        self._setpoints = dict([])

        self.dock_area = dockarea
        self.check_moving = False
        self.setup_ui()

        self.enable_controls_pid(False)

        self.enable_controls_pid_run(False)

        self.emit_curr_points_sig.connect(self.emit_curr_points)

    def ini_PID(self):

        if self.is_action_checked('ini_pid'):
            output_limits = [None, None]
            if self.settings['main_settings', 'pid_controls', 'output_limits', 'output_limit_min_enabled']:
                output_limits[0] = self.settings['main_settings', 'pid_controls', 'output_limits', 'output_limit_min']
            if self.settings['main_settings', 'pid_controls', 'output_limits', 'output_limit_max_enabled']:
                output_limits[1] = self.settings['main_settings', 'pid_controls', 'output_limits', 'output_limit_max']

            self.PIDThread = QThread()
            pid_runner = PIDRunner(self.model_class, self.modules_manager, setpoints=self.setpoints,
                                   params=dict(Kp=self.settings['main_settings', 'pid_controls', 'pid_constants',
                                                                      'kp'],
                                               Ki=self.settings['main_settings', 'pid_controls', 'pid_constants',
                                                                      'ki'],
                                               Kd=self.settings['main_settings', 'pid_controls', 'pid_constants',
                                                                      'kd'],
                                               sample_time=self.settings['main_settings', 'pid_controls',
                                                                               'sample_time'] / 1000,
                                               output_limits=output_limits,
                                               auto_mode=False),
                                   )

            self.PIDThread.pid_runner = pid_runner
            pid_runner.pid_output_signal.connect(self.process_output)
            pid_runner.status_sig.connect(self.thread_status)
            self.command_pid.connect(pid_runner.queue_command)

            pid_runner.moveToThread(self.PIDThread)

            self.PIDThread.start()
            self.get_action('pid_led').set_as_true()
            self.enable_controls_pid_run(True)

        else:
            if hasattr(self, 'PIDThread'):
                if self.PIDThread.isRunning():
                    try:
                        self.PIDThread.quit()
                    except Exception:
                        pass
            self.get_action('pid_led').set_as_false()
            self.enable_controls_pid_run(False)

        self.initialized_state = True

    def process_output(self, data: DataToExport):
        inputs: DataRaw = data.get_data_from_name('inputs')
        outputs: DataRaw = data.get_data_from_name('outputs')
        self.curr_points = [float(array[0]) for array in inputs]
        self.output_viewer.show_data(outputs)
        self.input_viewer.show_data(inputs)

    def enable_controls_pid(self, enable=False):
        self.set_action_enabled('ini_pid', enable)
        # self.setpoint_sb.setOpts(enabled=enable)

    def enable_controls_pid_run(self, enable=False):
        self.set_action_enabled('run', enable)
        self.set_action_enabled('pause', enable)

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

        elif param.name() == 'refresh_plot_time' or param.name() == 'timeout':
            self.command_pid.emit(ThreadCommand('update_timer', [param.name(), param.value()]))

        elif param.name() == 'sample_time':
            self.command_pid.emit(ThreadCommand('update_options', dict(sample_time=param.value())))

        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'pid_controls', 'output_limits'), []):

            output_limits = convert_output_limits(
                self.settings['main_settings', 'pid_controls', 'output_limits',
                              'output_limit_min'],
                self.settings['main_settings', 'pid_controls', 'output_limits',
                              'output_limit_min_enabled'],
                self.settings['main_settings', 'pid_controls', 'output_limits',
                              'output_limit_max'],
                self.settings['main_settings', 'pid_controls', 'output_limits',
                              'output_limit_max_enabled'])

            self.command_pid.emit(ThreadCommand('update_options', dict(output_limits=output_limits)))

        elif param.name() in putils.iter_children(
                self.settings.child('main_settings', 'pid_controls', 'pid_constants'), []):
            Kp = self.settings['main_settings', 'pid_controls', 'pid_constants', 'kp']
            Ki = self.settings['main_settings', 'pid_controls', 'pid_constants', 'ki']
            Kd = self.settings['main_settings', 'pid_controls', 'pid_constants', 'kd']
            self.command_pid.emit(ThreadCommand('update_options', dict(tunings=(Kp, Ki, Kd))))

        elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
            if self.model_class is not None:
                self.model_class.update_settings(param)

        elif param.name() == 'detector_modules':
            self.model_class.update_detector_names()

    def connect_things(self):
        logger.debug('connecting actions and other')
        self.connect_action('quit', self.quit_fun, )
        self.connect_action('ini_model', self.ini_model)
        self.connect_action('create_setp_actuators', self.create_setp_actuators)
        self.connect_action('ini_pid', self.ini_PID)
        self.connect_action('run', self.run_PID)
        self.connect_action('pause', self.pause_PID)
        logger.debug('connecting done')

    def setup_actions(self):
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.add_widget('model_label', QtWidgets.QLabel, 'Init Model:')
        self.add_action('ini_model', 'Init Model', 'ini', tip='Initialize the selected model: algo/data conversion')
        self.add_widget('model_led', QLED, toolbar=self.toolbar)

        self.add_action('create_setp_actuators', 'Create SetPoint Actuators', 'Add_Step',
                        tip='Create a DAQ_Move Control Module for each SetPoint allowing to'
                            'control them from the DashBoard, therefore within other extensions')

        self.add_widget('model_label', QtWidgets.QLabel, 'Init PID Runner:')
        self.add_action('ini_pid', 'Init the PID loop', 'ini', tip='Init the PID thread',
                        checkable=True)
        self.add_widget('pid_led', QLED, toolbar=self.toolbar)
        self.add_action('run', 'Run The PID loop', 'run2', tip='run or stop the pid loop',
                        checkable=True)
        self.add_action('pause', 'Pause the PID loop', 'pause', tip='Pause the PID loop',
                        checkable=True)
        self.set_action_checked('pause', True)
        self.set_action_enabled('create_setp_actuators', False)
        logger.debug('actions set')

    def setup_docks(self):
        logger.debug('settings the extension docks')
        self.dock_pid = Dock('PID controller', self.dock_area)
        self.dock_area.addDock(self.dock_pid)

        widget = QtWidgets.QWidget()
        widget_toolbar = QtWidgets.QWidget()
        verlayout = QtWidgets.QVBoxLayout()
        widget.setLayout(verlayout)
        self.toolbar_layout = QtWidgets.QGridLayout()
        widget_toolbar.setLayout(self.toolbar_layout)

        logger.debug('settings the extension docks done')

        labmaj = QtWidgets.QLabel('Sync Value:')
        self.toolbar_layout.addWidget(labmaj, 5, 0, 1, 2)

        verlayout.addWidget(widget_toolbar)
        verlayout.addWidget(self.settings_tree)

        self.dock_output = Dock('PID output')
        widget_output = QtWidgets.QWidget()
        self.output_viewer = Viewer0D(widget_output)
        self.dock_output.addWidget(widget_output)
        self.dock_area.addDock(self.dock_output, 'right', self.dock_pid)

        self.dock_input = Dock('PID input')
        widget_input = QtWidgets.QWidget()
        self.input_viewer = Viewer0D(widget_input)
        self.dock_input.addWidget(widget_input)
        self.dock_area.addDock(self.dock_input, 'bottom', self.dock_output)

        if len(self.models) != 0:
            self.get_set_model_params(self.models[0]['name'])

        self.dock_pid.addWidget(widget)

    def create_setp_actuators(self):
        # Now that we have the module manager, load PID if it is checked in managers
        try:
            for setp in self.model_class.setpoints_names:
                self.dashboard.add_move_from_extension(setp, 'PID', PIDController(self))
            self.set_action_enabled('create_setp_actuators', False)

        except Exception as e:
            raise PIDError('Could not load the PID extension and create setpoints actuators'
                           f'{str(e)}')

    def get_set_model_params(self, model_name):
        self.settings.child('models', 'model_params').clearChildren()
        models = get_models()
        if len(models) > 0:
            model_class = find_dict_in_list_from_key_val(models, 'name', model_name)['class']
            params = getattr(model_class, 'params')
            self.settings.child('models', 'model_params').addChildren(params)

    def run_PID(self):
        if self.is_action_checked('run'):
            self.get_action('run').set_icon('stop')
            self.command_pid.emit(ThreadCommand('start_PID', []))
            QtWidgets.QApplication.processEvents()

            QtWidgets.QApplication.processEvents()

            self.command_pid.emit(ThreadCommand('run_PID', [self.model_class.curr_output]))
        else:
            self.get_action('run').set_icon('run2')
            self.command_pid.emit(ThreadCommand('stop_PID'))

            QtWidgets.QApplication.processEvents()

    def pause_PID(self):
        for setp in self.setpoints_sb:
            setp.setEnabled(not self.is_action_checked('pause'))
        self.command_pid.emit(ThreadCommand('pause_PID', [self.is_action_checked('pause')]))

    def stop_moves(self, overshoot):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_Motion
        """
        self.overshoot = overshoot
        for mod in self.modules_manager.actuators:
            mod.stop_Motion()

    def set_model(self):
        model_name = self.settings['models', 'model_class']
        self.model_class = find_dict_in_list_from_key_val(self.models, 'name', model_name)['class'](self)
        self.set_setpoints_buttons()
        self.model_class.ini_model()
        self.settings.child('main_settings', 'epsilon').setValue(self.model_class.epsilon)

    def ini_model(self):
        try:
            if self.model_class is None:
                self.set_model()

            self.modules_manager.selected_actuators_name = self.model_class.actuators_name
            self.modules_manager.selected_detectors_name = self.model_class.detectors_name

            self.enable_controls_pid(True)
            self.get_action('model_led').set_as_true()
            self.set_action_enabled('ini_model', False)
            self.set_action_enabled('create_setp_actuators', True)

        except Exception as e:
            logger.exception(str(e))

    @property
    def setpoints(self):
        return [sp.value() for sp in self.setpoints_sb]

    @setpoints.setter
    def setpoints(self, values):
        for ind, sp in enumerate(self.setpoints_sb):
            sp.setValue(values[ind])

    def setpoints_external(self, values_dict: Dict[str, DataActuator]):
        for key in values_dict:
            index = self.model_class.setpoints_names.index(key)
            self.setpoints_sb[index].setValue(values_dict[key].value())

    @property
    def curr_points(self):
        return [sp.value() for sp in self.currpoints_sb]

    @curr_points.setter
    def curr_points(self, values):
        for ind, sp in enumerate(self.currpoints_sb):
            sp.setValue(values[ind])

    def emit_curr_points(self):
        if self.model_class is not None:
            self.curr_points_signal.emit(dict(zip(self.model_class.setpoints_names, self.curr_points)))

    def set_setpoints_buttons(self):
        self.setpoints_sb = []
        self.currpoints_sb = []
        self.syncvalue_pb = []
        for ind_set in range(self.model_class.Nsetpoints):

            label = LabelWithFont(self.model_class.setpoints_names[ind_set],
                                  font_name="Tahoma", font_size=14, isbold=True, isitalic=True)

            self.setpoints_sb.append(SpinBox())
            self.setpoints_sb[-1].setMinimumHeight(40)
            font = self.setpoints_sb[-1].font()
            font.setPointSizeF(20)
            self.setpoints_sb[-1].setFont(font)
            self.setpoints_sb[-1].setDecimals(6)
            self.toolbar_layout.addWidget(label, 2, 2 + ind_set, 1, 1)
            self.toolbar_layout.addWidget(self.setpoints_sb[-1], 3, 2 + ind_set, 1, 1)
            self.setpoints_sb[-1].valueChanged.connect(self.update_runner_setpoints)

            self.currpoints_sb.append(SpinBox())
            self.currpoints_sb[-1].setMinimumHeight(40)
            self.currpoints_sb[-1].setReadOnly(True)
            self.currpoints_sb[-1].setDecimals(6)
            self.currpoints_sb[-1].setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            font = self.currpoints_sb[-1].font()
            font.setPointSizeF(20)
            self.currpoints_sb[-1].setFont(font)
            self.toolbar_layout.addWidget(self.currpoints_sb[-1], 4, 2 + ind_set, 1, 1)

            self.syncvalue_pb.append(QtWidgets.QPushButton('Synchro {}'.format(ind_set)))
            self.syncvalue_pb[ind_set].clicked.connect(partial(self.currpoint_as_setpoint, ind_set))
            self.toolbar_layout.addWidget(self.syncvalue_pb[-1], 5, 2 + ind_set)
        self.setpoints_signal.connect(self.setpoints_external)

    def currpoint_as_setpoint(self, i=0):
        '''
        Function used by the sync buttons. The button i will attribute the value of the i-th currpoint to the i-th setpoint.
        '''
        self.setpoints_sb[i].setValue(self.curr_points[i])
        self.update_runner_setpoints

    def quit_fun(self):
        """
        """
        try:
            try:
                self.PIDThread.exit()
            except Exception as e:
                print(e)

            areas = self.dock_area.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()

            self.dock_area.parent().close()

        except Exception as e:
            print(e)

    def update_runner_setpoints(self):
        self.command_pid.emit(ThreadCommand('update_setpoints', self.setpoints))

    @Slot(list)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """

        """
        pass


class PIDRunner(QObject):
    status_sig = Signal(list)
    pid_output_signal = Signal(DataToExport)

    def __init__(self, model_class, modules_manager: ModulesManager, setpoints=[], params=dict([])):
        """
        Init the PID instance with params as initial conditions

        Parameters
        ----------
        params: (dict) Kp=1.0, Ki=0.0, Kd=0.0,setpoints=[0], sample_time=0.01, output_limits=(None, None),
                 auto_mode=True,
                 proportional_on_measurement=False)
        """
        super().__init__()
        self.model_class = model_class
        self.modules_manager = modules_manager
        Nsetpoints = model_class.Nsetpoints
        self.current_time = 0
        self.inputs_from_dets = DataToExport('inputs', data=[DataCalculated(self.model_class.setpoints_names[ind],
                                                                            data=[np.array([setpoints[ind]])])
                                                             for ind in range(Nsetpoints)])
        self.outputs = [0. for _ in range(Nsetpoints)]
        self.outputs_to_actuators = DataToActuators('pid',
                                                      mode='rel',
                                                      data=[DataActuator(self.model_class.actuators_name[ind],
                                                                         data=self.outputs[ind])
                                                            for ind in range(Nsetpoints)])

        if 'sample_time' in params:
            self.sample_time = params['sample_time']
        else:
            self.sample_time = 0.010  # in secs

        self.pids = [PID(setpoint=setpoints[0], **params) for ind in range(Nsetpoints)]  # #PID(object):
        for pid in self.pids:
            pid.set_auto_mode(False)
        self.refreshing_ouput_time = 200
        self.running = True
        self.timer = self.startTimer(self.refreshing_ouput_time)

        self.paused = True

    #     self.timeout_timer = QtCore.QTimer()
    #     self.timeout_timer.setInterval(10000)
    #     self.timeout_scan_flag = False
    #     self.timeout_timer.timeout.connect(self.timeout)
    #
    def timerEvent(self, event):
        outputs_dwa = self.outputs_to_actuators.merge_as_dwa('Data0D', name='outputs')
        outputs_dwa.labels = self.modules_manager.selected_actuators_name
        dte = DataToExport('toplot', data=[outputs_dwa])

        inputs_dwa = self.inputs_from_dets.merge_as_dwa('Data0D', name='inputs')
        inputs_dwa.labels = self.modules_manager.selected_actuators_name
        dte.append(inputs_dwa)
        self.pid_output_signal.emit(dte)

    @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand):
        """
        """
        if command.command == "start_PID":
            self.start_PID(*command.attribute)

        elif command.command == "run_PID":
            self.run_PID(*command.attribute)

        elif command.command == "pause_PID":
            self.pause_PID(*command.attribute)

        elif command.command == "stop_PID":
            self.stop_PID()

        elif command.command == 'update_options':
            self.set_option(**command.attribute)

        elif command.command == 'update_setpoints':
            self.update_setpoints(command.attribute)

        elif command.command == 'input':
            self.update_input(*command.attribute)

        elif command.command == 'update_timer':
            if command.attribute[0] == 'refresh_plot_time':
                self.killTimer(self.timer)
                self.refreshing_ouput_time = command.attribute[1]
                self.timer = self.startTimer(self.refreshing_ouput_time)
            elif command.attribute[0] == 'timeout':
                self.timeout_timer.setInterval(command.attribute[1])

    def update_input(self, measurements: DataToExport):
        self.inputs_from_dets = self.model_class.convert_input(measurements)

    def start_PID(self, sync_detectors=True, sync_acts=False):
        """Start the pid controller loop

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
            logger.info('PID loop starting')
            while self.running:
                # print('input: {}'.format(self.input))
                # # GRAB DATA FIRST AND WAIT ALL DETECTORS RETURNED

                self.det_done_datas: DataToExport = self.modules_manager.grab_datas()

                self.inputs_from_dets: DataToExport = self.model_class.convert_input(self.det_done_datas)

                # # EXECUTE THE PID
                self.outputs = []
                for ind, pid in enumerate(self.pids):
                    self.outputs.append(pid(float(self.inputs_from_dets[ind][0][0])))

                # # APPLY THE PID OUTPUT TO THE ACTUATORS
                if self.outputs is None:
                    self.outputs = [pid.setpoint for pid in self.pids]

                dt = time.perf_counter() - self.current_time
                self.outputs_to_actuators: DataToActuators = (
                    self.model_class.convert_output(self.outputs, dt, stab=True))

                if not self.paused:
                    self.modules_manager.move_actuators(self.outputs_to_actuators,
                                                        self.outputs_to_actuators.mode,
                                                        polling=False)

                self.current_time = time.perf_counter()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(int(self.sample_time * 1000))

            logger.info('PID loop exiting')
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

        except Exception as e:
            logger.exception(str(e))

    def update_setpoints(self, setpoints):
        for ind, pid in enumerate(self.pids):
            pid.setpoint = setpoints[ind]

    def set_option(self, **option):
        for pid in self.pids:
            for key in option:
                if hasattr(pid, key):
                    if key == 'sample_time':
                        setattr(pid, key, option[key] / 1000)
                    else:
                        setattr(pid, key, option[key])

    def run_PID(self, last_values):
        logger.info('Stabilization started')
        for ind, pid in enumerate(self.pids):
            pid.set_auto_mode(True, last_values[ind])

    def pause_PID(self, pause_state):
        for ind, pid in enumerate(self.pids):
            if pause_state:
                pid.set_auto_mode(False)
                logger.info('Stabilization paused')
            else:
                pid.set_auto_mode(True, self.outputs[ind])
                logger.info('Stabilization restarted from pause')
        self.paused = pause_state

    def stop_PID(self):
        self.running = False
        logger.info('PID loop exiting')


if __name__ == '__main__':
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('DAQ_PID')
    preset_file_name = config('presets', f'default_preset_for_pid')

    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, 'DAQ_PID')

    app.exec()






