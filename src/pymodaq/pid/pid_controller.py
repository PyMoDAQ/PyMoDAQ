import os
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale

from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_param_from_param, set_logger, get_module_name, \
    get_set_pid_path, get_models, find_dict_in_list_from_key_val
from pymodaq.daq_utils.managers.modules_manager import ModulesManager
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.parameter.pymodaq_ptypes as custom_tree
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.pid.utils import OutputToActuator, InputFromDetector

import importlib
from simple_pid import PID
import time
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_move.daq_move_main import DAQ_Move
import numpy as np

logger = set_logger(get_module_name(__file__))

def convert_output_limits(lim_min=-10., min_status=False, lim_max=10., max_status=False):
    output = [None, None]
    if min_status:
        output[0] = lim_min
    if max_status:
        output[1] = lim_max
    return output


class DAQ_PID(QObject):
    """
    """
    command_pid = pyqtSignal(ThreadCommand)
    curr_points_signal = pyqtSignal(dict)
    setpoints_signal = pyqtSignal(dict)
    emit_curr_points_sig = pyqtSignal()

    models = get_models()

    params = [
        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True, 'children': [
            {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
             'values': [d['name'] for d in models]},
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

    def __init__(self, dockarea):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__()

        self.settings = Parameter.create(title='PID settings', name='pid_settings', type='group', children=self.params)
        self.title = 'PyMoDAQ PID'

        self.Initialized_state = False
        self.model_class = None
        self._curr_points = dict([])
        self._setpoints = dict([])

        self.modules_manager = None

        self.dock_area = dockarea
        self.check_moving = False
        self.setupUI()

        self.enable_controls_pid(False)

        self.enable_controls_pid_run(False)

        self.emit_curr_points_sig.connect(self.emit_curr_points)

    def set_module_manager(self, detector_modules, actuator_modules):
        self.modules_manager = ModulesManager(detector_modules, actuator_modules)

    def ini_PID(self):

        if self.ini_PID_action.isChecked():
            output_limits = [None, None]
            if self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                   'output_limit_min_enabled').value():
                output_limits[0] = self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                                       'output_limit_min').value()
            if self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                   'output_limit_max_enabled').value():
                output_limits[1] = self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                                       'output_limit_max').value()

            self.PIDThread = QThread()
            pid_runner = PIDRunner(self.model_class, self.modules_manager, setpoints=self.setpoints,
                                   params=dict(Kp=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                                      'kp').value(),
                                               Ki=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                                      'ki').value(),
                                               Kd=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                                      'kd').value(),
                                               sample_time=self.settings.child('main_settings', 'pid_controls',
                                                                               'sample_time').value() / 1000,
                                               output_limits=output_limits,
                                               auto_mode=False),
                                   )

            self.PIDThread.pid_runner = pid_runner
            pid_runner.pid_output_signal.connect(self.process_output)
            pid_runner.status_sig.connect(self.thread_status)
            self.command_pid.connect(pid_runner.queue_command)

            pid_runner.moveToThread(self.PIDThread)

            self.PIDThread.start()
            self.pid_led.set_as_true()
            self.enable_controls_pid_run(True)

        else:
            if hasattr(self, 'PIDThread'):
                if self.PIDThread.isRunning():
                    try:
                        self.PIDThread.quit()
                    except Exception:
                        pass
            self.pid_led.set_as_false()
            self.enable_controls_pid_run(False)

        self.Initialized_state = True

    def process_output(self, datas):
        self.output_viewer.show_data([[dat] for dat in datas['output']])
        self.input_viewer.show_data([[dat] for dat in datas['input']])
        self.curr_points = datas['input']

    def enable_controls_pid(self, enable=False):
        self.ini_PID_action.setEnabled(enable)
        #self.setpoint_sb.setOpts(enabled=enable)

    def enable_controls_pid_run(self, enable=False):
        self.run_action.setEnabled(enable)
        self.pause_action.setEnabled(enable)

    def setupUI(self):

        self.dock_pid = gutils.Dock('PID controller', self.dock_area)
        self.dock_area.addDock(self.dock_pid)

        widget = QtWidgets.QWidget()
        widget_toolbar = QtWidgets.QWidget()
        verlayout = QtWidgets.QVBoxLayout()
        widget.setLayout(verlayout)
        self.toolbar_layout = QtWidgets.QGridLayout()
        widget_toolbar.setLayout(self.toolbar_layout)

        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.quit_action = QtWidgets.QPushButton(iconquit, "Quit")
        self.quit_action.setToolTip('Quit the application')
        self.toolbar_layout.addWidget(self.quit_action, 0, 0, 1, 2)
        self.quit_action.clicked.connect(self.quit_fun)

        iconini = QtGui.QIcon()
        iconini.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/ini.png"), QtGui.QIcon.Normal,
                          QtGui.QIcon.Off)
        self.ini_model_action = QtWidgets.QPushButton(iconini, "Init Model")
        self.ini_model_action.setToolTip('Initialize the chosen model')
        self.toolbar_layout.addWidget(self.ini_model_action, 2, 0)
        self.ini_model_action.clicked.connect(self.ini_model)
        self.model_led = QLED()
        self.toolbar_layout.addWidget(self.model_led, 2, 1)

        self.ini_PID_action = QtWidgets.QPushButton(iconini, "Init PID")
        self.ini_PID_action.setToolTip('Initialize the PID loop')
        self.toolbar_layout.addWidget(self.ini_PID_action, 2, 2)
        self.ini_PID_action.setCheckable(True)
        self.ini_PID_action.clicked.connect(self.ini_PID)
        self.pid_led = QLED()
        self.toolbar_layout.addWidget(self.pid_led, 2, 3)

        self.iconrun = QtGui.QIcon()
        self.iconrun.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
        self.icon_stop = QtGui.QIcon()
        self.icon_stop.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/stop.png"))
        self.run_action = QtWidgets.QPushButton(self.iconrun, "", None)
        self.run_action.setToolTip('Start PID loop')
        self.run_action.setCheckable(True)
        self.toolbar_layout.addWidget(self.run_action, 0, 2)
        self.run_action.clicked.connect(self.run_PID)

        iconpause = QtGui.QIcon()
        iconpause.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/pause.png"), QtGui.QIcon.Normal,
                            QtGui.QIcon.Off)
        self.pause_action = QtWidgets.QPushButton(iconpause, "", None)
        self.pause_action.setToolTip('Pause PID')
        self.pause_action.setCheckable(True)
        self.toolbar_layout.addWidget(self.pause_action, 0, 3)
        self.pause_action.setChecked(True)
        self.pause_action.clicked.connect(self.pause_PID)

        lab = QtWidgets.QLabel('Target Value:')
        self.toolbar_layout.addWidget(lab, 3, 0, 1, 2)


        lab1 = QtWidgets.QLabel('Current Value:')
        self.toolbar_layout.addWidget(lab1, 4, 0, 1, 2)


        # create main parameter tree
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)

        verlayout.addWidget(widget_toolbar)
        verlayout.addWidget(self.settings_tree)

        self.dock_output = gutils.Dock('PID output')
        widget_output = QtWidgets.QWidget()
        self.output_viewer = Viewer0D(widget_output)
        self.dock_output.addWidget(widget_output)
        self.dock_area.addDock(self.dock_output, 'right', self.dock_pid)

        self.dock_input = gutils.Dock('PID input')
        widget_input = QtWidgets.QWidget()
        self.input_viewer = Viewer0D(widget_input)
        self.dock_input.addWidget(widget_input)
        self.dock_area.addDock(self.dock_input, 'bottom', self.dock_output)

        if len(self.models) != 0:
            self.get_set_model_params(self.models[0])

        # connecting from tree
        self.settings.sigTreeStateChanged.connect(
            self.parameter_tree_changed)  # any changes on the settings will update accordingly the detector
        self.dock_pid.addWidget(widget)

    def get_set_model_params(self, model):
        self.settings.child('models', 'model_params').clearChildren()
        model_class = find_dict_in_list_from_key_val(get_models(), 'name', model['name'])['class']
        params = getattr(model_class, 'params')
        self.settings.child('models', 'model_params').addChildren(params)

    def run_PID(self):
        if self.run_action.isChecked():
            self.run_action.setIcon(self.icon_stop)
            self.command_pid.emit(ThreadCommand('start_PID', []))
            QtWidgets.QApplication.processEvents()

            QtWidgets.QApplication.processEvents()

            self.command_pid.emit(ThreadCommand('run_PID', [self.model_class.curr_output]))
        else:
            self.run_action.setIcon(self.iconrun)
            self.command_pid.emit(ThreadCommand('stop_PID'))

            QtWidgets.QApplication.processEvents()

    def pause_PID(self):
        for setp in self.setpoints_sb:
            setp.setEnabled(not self.pause_action.isChecked())
        self.command_pid.emit(ThreadCommand('pause_PID', [self.pause_action.isChecked()]))


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
        model_name = self.settings.child('models', 'model_class').value()
        self.model_class = find_dict_in_list_from_key_val(self.models, 'name', model_name)['class'](self)
        self.set_setpoints_buttons()
        self.model_class.ini_model()

    def ini_model(self):
        try:
            if self.model_class is None:
                self.set_model()

            self.modules_manager.selected_actuators_name = self.model_class.actuators_name
            self.modules_manager.selected_detectors_name = self.model_class.detectors_name

            self.enable_controls_pid(True)
            self.model_led.set_as_true()
            self.ini_model_action.setEnabled(False)

        except Exception as e:
            logger.exception(str(e))

    @property
    def setpoints(self):
        return [sp.value() for sp in self.setpoints_sb]

    @setpoints.setter
    def setpoints(self, values):
        for ind, sp in enumerate(self.setpoints_sb):
            sp.setValue(values[ind])

    def setpoints_external(self, values_dict):
        for key in values_dict:
            index = self.model_class.setpoints_names.index(key)
            self.setpoints_sb[index].setValue(values_dict[key])

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
        for ind_set in range(self.model_class.Nsetpoints):

            self.setpoints_sb.append(custom_tree.SpinBoxCustom())
            self.setpoints_sb[-1].setMinimumHeight(40)
            font = self.setpoints_sb[-1].font()
            font.setPointSizeF(20)
            self.setpoints_sb[-1].setFont(font)
            self.setpoints_sb[-1].setDecimals(6)
            self.toolbar_layout.addWidget(self.setpoints_sb[-1], 3, 2+ind_set, 1, 1)
            self.setpoints_sb[-1].valueChanged.connect(self.update_runner_setpoints)


            self.currpoints_sb.append(custom_tree.SpinBoxCustom())
            self.currpoints_sb[-1].setMinimumHeight(40)
            self.currpoints_sb[-1].setReadOnly(True)
            self.currpoints_sb[-1].setDecimals(6)
            self.currpoints_sb[-1].setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            font = self.currpoints_sb[-1].font()
            font.setPointSizeF(20)
            self.currpoints_sb[-1].setFont(font)
            self.toolbar_layout.addWidget(self.currpoints_sb[-1], 4, 2+ind_set, 1, 1)

        self.setpoints_signal.connect(self.setpoints_external)

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

    def parameter_tree_changed(self, param, changes):
        """
            Foreach value changed, update :
                * Viewer in case of **DAQ_type** parameter name
                * visibility of button in case of **show_averaging** parameter name
                * visibility of naverage in case of **live_averaging** parameter name
                * scale of axis **else** (in 2D pymodaq type)

            Once done emit the update settings signal to link the commit.

            =============== =================================== ================================================================
            **Parameters**    **Type**                           **Description**
            *param*           instance of ppyqtgraph parameter   the parameter to be checked
            *changes*         tuple list                         Contain the (param,changes,info) list listing the changes made
            =============== =================================== ================================================================
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'model_class':
                    self.get_set_model_params(param.value())

                elif param.name() == 'refresh_plot_time' or param.name() == 'timeout':
                    self.command_pid.emit(ThreadCommand('update_timer', [param.name(), param.value()]))

                elif param.name() == 'sample_time':
                    self.command_pid.emit(ThreadCommand('update_options', dict(sample_time=param.value())))

                elif param.name() in putils.iter_children(
                        self.settings.child('main_settings', 'pid_controls', 'output_limits'), []):


                    output_limits = convert_output_limits(
                        self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                            'output_limit_min').value(),
                        self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                           'output_limit_min_enabled').value(),
                        self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                                               'output_limit_max').value(),
                        self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                           'output_limit_max_enabled').value())

                    self.command_pid.emit(ThreadCommand('update_options', dict(output_limits=output_limits)))

                elif param.name() in putils.iter_children(
                        self.settings.child('main_settings', 'pid_controls', 'pid_constants'), []):
                    Kp = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kp').value()
                    Ki = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'ki').value()
                    Kd = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kd').value()
                    self.command_pid.emit(ThreadCommand('update_options', dict(tunings=(Kp, Ki, Kd))))

                elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
                    if self.model_class is not None:
                        self.model_class.update_settings(param)

                elif param.name() == 'detector_modules':
                    self.model_class.update_detector_names()

            elif change == 'parent':
                pass

    def update_runner_setpoints(self):
        self.command_pid.emit(ThreadCommand('update_setpoints', self.setpoints))

    @pyqtSlot(list)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """

        """
        pass


class PIDRunner(QObject):
    status_sig = pyqtSignal(list)
    pid_output_signal = pyqtSignal(dict)

    def __init__(self, model_class, module_manager, setpoints=[], params=dict([])):
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
        self.modules_manager = module_manager
        Nsetpoints = model_class.Nsetpoints
        self.current_time = 0
        self.inputs_from_dets = InputFromDetector(values=setpoints)
        self.outputs = None
        self.outputs_to_actuators = OutputToActuator(values=[0. for ind in range(Nsetpoints)])

        if 'sample_time' in params:
            self.sample_time = params['sample_time']
        else:
            self.sample_time = 0.010  # in secs

        self.pids = [PID(setpoint=setpoints[0], **params) for ind in range(Nsetpoints)] # #PID(object):
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
       self.pid_output_signal.emit(dict(output=self.outputs_to_actuators.values,
                                             input=self.inputs_from_dets.values))

    @pyqtSlot(ThreadCommand)
    def queue_command(self, command=ThreadCommand()):
        """
        """
        if command.command == "start_PID":
            self.start_PID(*command.attributes)

        elif command.command == "run_PID":
            self.run_PID(*command.attributes)

        elif command.command == "pause_PID":
            self.pause_PID(*command.attributes)

        elif command.command == "stop_PID":
            self.stop_PID()

        elif command.command == 'update_options':
            self.set_option(**command.attributes)

        elif command.command == 'update_setpoints':
            self.update_setpoints(command.attributes)

        elif command.command == 'input':
            self.update_input(*command.attributes)

        elif command.command == 'update_timer':
            if command.attributes[0] == 'refresh_plot_time':
                self.killTimer(self.timer)
                self.refreshing_ouput_time = command.attributes[1]
                self.timer = self.startTimer(self.refreshing_ouput_time)
            elif command.attributes[0] == 'timeout':
                self.timeout_timer.setInterval(command.attributes[1])

    def update_input(self, measurements):
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

                self.det_done_datas = self.modules_manager.grab_datas()

                self.inputs_from_dets = self.model_class.convert_input(self.det_done_datas)

                # # EXECUTE THE PID
                self.outputs = []
                for ind, pid in enumerate(self.pids):
                    self.outputs.append(pid(self.inputs_from_dets.values[ind]))

                # # APPLY THE PID OUTPUT TO THE ACTUATORS
                if self.outputs is None:
                    self.outputs = [pid.setpoint for pid in self.pids]

                dt = time.perf_counter() - self.current_time
                self.outputs_to_actuators = self.model_class.convert_output(self.outputs, dt, stab=True)

                if not self.paused:
                    self.modules_manager.move_actuators(self.outputs_to_actuators.values,
                                                       self.outputs_to_actuators.mode,
                                                       poll=False)

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


def main():
    from pymodaq.dashboard import DashBoard
    from pymodaq.daq_utils.daq_utils import get_set_preset_path
    from pathlib import Path
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dashboard = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath("BeamSteering.xml")
    if file.exists():
        dashboard.set_preset_mode(file)
        # prog.load_scan_module()
        pid_area = gutils.DockArea()
        pid_window = QtWidgets.QMainWindow()
        pid_window.setCentralWidget(pid_area)

        prog = DAQ_PID(pid_area)
        pid_window.show()
        pid_window.setWindowTitle('PidController')
        prog.set_module_manager(dashboard.detector_modules, dashboard.actuators_modules)
        QtWidgets.QApplication.processEvents()


    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_PID Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



