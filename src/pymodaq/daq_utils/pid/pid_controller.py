import os
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale
import logging

from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_param_from_param, getLineInfo, set_logger, get_module_name, \
    get_set_pid_path

from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.parameter.pymodaq_ptypes as custom_tree
from pymodaq.daq_utils.gui_utils import DockArea
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils.managers.preset_manager import PresetManager
from pyqtgraph.dockarea import Dock

import importlib
from simple_pid import PID
import time
import datetime
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_move.daq_move_main import DAQ_Move
import numpy as np
from collections import OrderedDict
from pymodaq.daq_utils.pid.pid_params import params

logger = set_logger(get_module_name(__file__))


class DAQ_PID(QObject):
    """
    """
    log_signal = pyqtSignal(str)
    # look for eventual model files
    command_pid = pyqtSignal(ThreadCommand)
    command_stage = pyqtSignal(ThreadCommand)
    move_done_signal = pyqtSignal(str, float)

    models = []
    try:
        model_mod = importlib.import_module('pymodaq_pid_models')
        for ind_file, entry in enumerate(os.scandir(os.path.join(model_mod.__path__[0], 'models'))):
            if not entry.is_dir() and entry.name != '__init__.py':
                try:
                    file, ext = os.path.splitext(entry.name)
                    importlib.import_module('.' + file, model_mod.__name__ + '.models')

                    models.append(file)
                except Exception as e:
                    logger.exception(str(e))
        if 'PIDModelMock' in models:
            mods = models
            mods.pop(models.index('PIDModelMock'))
            models = ['PIDModelMock']
            models.extend(mods)

    except Exception as e:
        logger.exception(str(e))

    if len(models) == 0:
        logger.warning('No valid installed models')

    def __init__(self, area, detector_modules=[], actuator_modules=[]):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_PID, self).__init__()

        self.settings = Parameter.create(title='PID settings', name='pid_settings', type='group', children=params)
        self.title = 'PyMoDAQ PID'
        self.Initialized_state = False
        self.model_class = None
        self.detector_modules = detector_modules
        self.actuator_modules = actuator_modules
        self.dock_area = area
        self.overshoot = None
        self.check_moving = False
        self.preset_manager = PresetManager()
        self.setupUI()
        self.command_stage.connect(self.move_Abs)  # to be compatible with actuator modules within daq scan

        self.enable_controls_pid(False)

        self.enable_controls_pid_run(False)

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
            pid_runner = PIDRunner(self.model_class,
                                   [mod.move_done_signal for mod in self.actuator_modules],
                                   [mod.grab_done_signal for mod in self.detector_modules],
                                   [mod.command_stage for mod in self.actuator_modules],
                                   [mod.command_detector for mod in self.detector_modules],
                                   dict(Kp=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                               'kp').value(),
                                        Ki=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                               'ki').value(),
                                        Kd=self.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                                               'kd').value(),
                                        setpoint=self.settings.child('main_settings', 'pid_controls',
                                                                     'set_point').value(),
                                        sample_time=self.settings.child('main_settings', 'pid_controls',
                                                                        'sample_time').value() / 1000,
                                        output_limits=output_limits,
                                        auto_mode=False),
                                   filter=dict(enable=self.settings.child('main_settings', 'pid_controls', 'filter',
                                                                          'filter_enable').value(),
                                               value=self.settings.child('main_settings', 'pid_controls', 'filter',
                                                                         'filter_step').value()),
                                   det_averaging=[mod.settings.child('main_settings', 'Naverage').value() for mod in
                                                  self.detector_modules],
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

    pyqtSlot(dict)

    def process_output(self, datas):
        self.output_viewer.show_data([[dat] for dat in datas['output']])
        self.input_viewer.show_data([[dat] for dat in datas['input']])
        self.currpoint_sb.setValue(np.mean(datas['input']))

        if self.check_moving:
            if np.abs(np.mean(datas['input']) - self.settings.child('main_settings', 'pid_controls',
                                                                    'set_point').value()) < \
                    self.settings.child('main_settings', 'epsilon').value():
                self.move_done_signal.emit(self.title, np.mean(datas['input']))
                self.check_moving = False
                print('Move from {:s} is done: {:f}'.format('PID', np.mean(datas['input'])))

    @pyqtSlot(ThreadCommand)
    def move_Abs(self, command=ThreadCommand()):
        """
        """
        if command.command == "move_Abs":
            self.check_moving = True
            self.setpoint_sb.setValue(command.attributes[0])
            QtWidgets.QApplication.processEvents()

    def enable_controls_pid(self, enable=False):
        self.ini_PID_action.setEnabled(enable)
        self.setpoint_sb.setOpts(enabled=enable)

    def enable_controls_pid_run(self, enable=False):
        self.run_action.setEnabled(enable)
        self.pause_action.setEnabled(enable)

    def setupUI(self):

        self.dock_pid = Dock('PID controller', self.dock_area)
        self.dock_area.addDock(self.dock_pid)

        # %% create logger dock
        self.logger_dock = Dock("Logger")
        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.logger_dock.addWidget(self.logger_list)
        self.dock_area.addDock(self.logger_dock, 'right')
        self.logger_dock.setVisible(True)

        widget = QtWidgets.QWidget()
        widget_toolbar = QtWidgets.QWidget()
        verlayout = QtWidgets.QVBoxLayout()
        widget.setLayout(verlayout)
        toolbar_layout = QtWidgets.QGridLayout()
        widget_toolbar.setLayout(toolbar_layout)

        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.quit_action = QtWidgets.QPushButton(iconquit, "Quit")
        self.quit_action.setToolTip('Quit the application')
        toolbar_layout.addWidget(self.quit_action, 0, 0, 1, 2)
        self.quit_action.clicked.connect(self.quit_fun)

        iconini = QtGui.QIcon()
        iconini.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/ini.png"), QtGui.QIcon.Normal,
                          QtGui.QIcon.Off)
        self.ini_model_action = QtWidgets.QPushButton(iconini, "Init Model")
        self.ini_model_action.setToolTip('Initialize the chosen model')
        toolbar_layout.addWidget(self.ini_model_action, 2, 0)
        self.ini_model_action.clicked.connect(self.ini_model)
        self.model_led = QLED()
        toolbar_layout.addWidget(self.model_led, 2, 1)

        self.ini_PID_action = QtWidgets.QPushButton(iconini, "Init PID")
        self.ini_PID_action.setToolTip('Initialize the PID loop')
        toolbar_layout.addWidget(self.ini_PID_action, 2, 2)
        self.ini_PID_action.setCheckable(True)
        self.ini_PID_action.clicked.connect(self.ini_PID)
        self.pid_led = QLED()
        toolbar_layout.addWidget(self.pid_led, 2, 3)

        self.iconrun = QtGui.QIcon()
        self.iconrun.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
        self.icon_stop = QtGui.QIcon()
        self.icon_stop.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/stop.png"))
        self.run_action = QtWidgets.QPushButton(self.iconrun, "", None)
        self.run_action.setToolTip('Start PID loop')
        self.run_action.setCheckable(True)
        toolbar_layout.addWidget(self.run_action, 0, 2)
        self.run_action.clicked.connect(self.run_PID)

        iconpause = QtGui.QIcon()
        iconpause.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/pause.png"), QtGui.QIcon.Normal,
                            QtGui.QIcon.Off)
        self.pause_action = QtWidgets.QPushButton(iconpause, "", None)
        self.pause_action.setToolTip('Pause PID')
        self.pause_action.setCheckable(True)
        toolbar_layout.addWidget(self.pause_action, 0, 3)
        self.pause_action.setChecked(True)
        self.pause_action.clicked.connect(self.pause_PID)

        lab = QtWidgets.QLabel('Set Point:')
        toolbar_layout.addWidget(lab, 3, 0, 1, 2)

        self.setpoint_sb = custom_tree.SpinBoxCustom()
        self.setpoint_sb.setMinimumHeight(40)
        font = self.setpoint_sb.font()
        font.setPointSizeF(20)
        self.setpoint_sb.setFont(font)
        self.setpoint_sb.setDecimals(6)
        toolbar_layout.addWidget(self.setpoint_sb, 3, 2, 1, 2)
        self.setpoint_sb.valueChanged.connect(
            self.settings.child('main_settings', 'pid_controls', 'set_point').setValue)

        lab1 = QtWidgets.QLabel('Current Point:')
        toolbar_layout.addWidget(lab1, 4, 0, 1, 2)

        self.currpoint_sb = custom_tree.SpinBoxCustom()
        self.currpoint_sb.setMinimumHeight(40)
        self.currpoint_sb.setReadOnly(True)
        self.currpoint_sb.setDecimals(6)
        self.currpoint_sb.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        font = self.currpoint_sb.font()
        font.setPointSizeF(20)
        self.currpoint_sb.setFont(font)
        toolbar_layout.addWidget(self.currpoint_sb, 4, 2, 1, 2)

        # create main parameter tree
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)

        verlayout.addWidget(widget_toolbar)
        verlayout.addWidget(self.settings_tree)

        self.dock_output = Dock('PID output')
        widget_output = QtWidgets.QWidget()
        self.output_viewer = Viewer0D(widget_output)
        self.dock_output.addWidget(widget_output)
        self.dock_area.addDock(self.dock_output, 'right')

        self.dock_input = Dock('PID input')
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

    def get_set_model_params(self, model_file):
        self.settings.child('models', 'model_params').clearChildren()
        model = importlib.import_module('.' + model_file, self.model_mod.__name__ + '.models')
        model_class = getattr(model, model_file)
        params = getattr(model_class, 'params')
        self.settings.child('models', 'model_params').addChildren(params)

    def run_PID(self):
        if self.run_action.isChecked():
            self.run_action.setIcon(self.icon_stop)
            self.command_pid.emit(ThreadCommand('start_PID', [self.model_class.curr_input]))
            QtWidgets.QApplication.processEvents()

            QtWidgets.QApplication.processEvents()

            self.command_pid.emit(ThreadCommand('run_PID', [self.model_class.curr_output]))
        else:
            self.run_action.setIcon(self.iconrun)
            self.command_pid.emit(ThreadCommand('stop_PID'))

            QtWidgets.QApplication.processEvents()

    def pause_PID(self):
        self.command_pid.emit(ThreadCommand('pause_PID', [self.pause_action.isChecked()]))

    def update_status(self, txt, log_type=None):
        """
            Show the txt message in the status bar with a delay of wait_time ms.

            =============== =========== =======================
            **Parameters**    **Type**    **Description**
            *txt*             string      The message to show
            *wait_time*       int         the delay of showing
            *log_type*        string      the type of the log
            =============== =========== =======================
        """
        try:
            if log_type is not None:
                self.log_signal.emit(txt)
                logging.info(txt)
        except Exception as e:
            pass

    @pyqtSlot(str)
    def add_log(self, txt):
        """
            Add the QListWisgetItem initialized with txt informations to the User Interface logger_list and to the save_parameters.logger array.

            =============== =========== ======================
            **Parameters**    **Type**   **Description**
            *txt*             string     the log info to add.
            =============== =========== ======================
        """
        try:
            now = datetime.datetime.now()
            new_item = QtWidgets.QListWidgetItem(now.strftime('%Y/%m/%d %H:%M:%S') + ": " + txt)
            self.logger_list.addItem(new_item)
        except Exception:
            pass

    def set_file_preset(self, model):
        """
            Set a file managers from the converted xml file given by the filename parameter.


            =============== =========== ===================================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the xml file to be converted/treated
            =============== =========== ===================================================

            Returns
            -------
            (Object list, Object list) tuple
                The updated (Move modules list, Detector modules list).

            See Also
            --------
            custom_tree.XML_file_to_parameter, set_param_from_param, stop_moves, update_status,DAQ_Move_main.daq_move, DAQ_viewer_main.daq_viewer
        """

        filename = os.path.join(get_set_pid_path(), model + '.xml')
        self.preset_file = filename
        self.preset_manager.set_file_preset(filename, show=False)
        self.move_docks = []
        self.det_docks_settings = []
        self.det_docks_viewer = []
        move_forms = []
        actuator_modules = []
        detector_modules = []
        move_types = []

        # ################################################################
        # ##### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins = [{'type': 'move', 'value': child} for child in
                   self.preset_manager.preset_params.child(('Moves')).children()] + [{'type': 'det', 'value': child} for
                                                                                     child in
                                                                                     self.preset_manager.preset_params.child(
                                                                                         ('Detectors')).children()]

        for plug in plugins:
            plug['ID'] = plug['value'].child('params', 'main_settings', 'controller_ID').value()
            if plug["type"] == 'det':
                plug['status'] = plug['value'].child('params', 'detector_settings', 'controller_status').value()
            else:
                plug['status'] = plug['value'].child('params', 'move_settings', 'multiaxes', 'multi_status').value()

        IDs = list(set([plug['ID'] for plug in plugins]))
        # %%
        plugins_sorted = []
        for id in IDs:
            plug_Ids = []
            for plug in plugins:
                if plug['ID'] == id:
                    plug_Ids.append(plug)
            plug_Ids.sort(key=lambda status: status['status'])
            plugins_sorted.append(plug_Ids)
        #################################################################
        #######################

        ind_move = -1
        ind_det = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):

                plug_name = plugin['value'].child(('name')).value()
                plug_init = plugin['value'].child(('init')).value()
                plug_settings = plugin['value'].child(('params'))

                if plugin['type'] == 'move':
                    ind_move += 1
                    plug_type = plug_settings.child('main_settings', 'move_type').value()
                    self.move_docks.append(Dock(plug_name, size=(150, 250)))
                    if ind_move == 0:
                        self.dock_area.addDock(self.move_docks[-1], 'top', self.logger_dock)
                    else:
                        self.dock_area.addDock(self.move_docks[-1], 'above', self.move_docks[-2])
                    move_forms.append(QtWidgets.QWidget())
                    mov_mod_tmp = DAQ_Move(move_forms[-1], plug_name)

                    mov_mod_tmp.ui.Stage_type_combo.setCurrentText(plug_type)
                    mov_mod_tmp.ui.Quit_pb.setEnabled(False)
                    QtWidgets.QApplication.processEvents()

                    set_param_from_param(mov_mod_tmp.settings, plug_settings)
                    QtWidgets.QApplication.processEvents()

                    mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
                    self.move_docks[-1].addWidget(move_forms[-1])
                    actuator_modules.append(mov_mod_tmp)

                    try:
                        if ind_plugin == 0:  # should be a master type plugin
                            if plugin['status'] != "Master":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                actuator_modules[-1].ui.IniStage_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_type:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                                master_controller = actuator_modules[-1].controller
                        else:
                            if plugin['status'] != "Slave":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                actuator_modules[-1].controller = master_controller
                                actuator_modules[-1].ui.IniStage_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_type:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                    except Exception as e:
                        self.update_status(getLineInfo() + str(e), 'log')

                else:
                    ind_det += 1
                    plug_type = plug_settings.child('main_settings', 'DAQ_type').value()
                    plug_subtype = plug_settings.child('main_settings', 'detector_type').value()

                    self.det_docks_settings.append(Dock(plug_name + " settings", size=(150, 250)))
                    self.det_docks_viewer.append(Dock(plug_name + " viewer", size=(350, 350)))

                    if ind_det == 0:
                        self.logger_dock.area.addDock(self.det_docks_settings[-1], 'bottom',
                                                      self.dock_input)  # dock_area of the logger dock
                    else:
                        self.dock_area.addDock(self.det_docks_settings[-1], 'bottom', self.det_docks_settings[-2])
                    self.dock_area.addDock(self.det_docks_viewer[-1], 'right', self.det_docks_settings[-1])

                    det_mod_tmp = DAQ_Viewer(self.dock_area, dock_settings=self.det_docks_settings[-1],
                                             dock_viewer=self.det_docks_viewer[-1], title=plug_name,
                                             DAQ_type=plug_type, parent_scan=self)
                    detector_modules.append(det_mod_tmp)
                    detector_modules[-1].ui.Detector_type_combo.setCurrentText(plug_subtype)
                    detector_modules[-1].ui.Quit_pb.setEnabled(False)
                    set_param_from_param(det_mod_tmp.settings, plug_settings)
                    QtWidgets.QApplication.processEvents()

                    try:
                        if ind_plugin == 0:  # should be a master type plugin
                            if plugin['status'] != "Master":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                detector_modules[-1].ui.IniDet_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_subtype:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                                master_controller = detector_modules[-1].controller
                        else:
                            if plugin['status'] != "Slave":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                detector_modules[-1].controller = master_controller
                                detector_modules[-1].ui.IniDet_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_subtype:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                    except Exception as e:
                        self.update_status(getLineInfo() + str(e), 'log')

                    detector_modules[-1].settings.child('main_settings', 'overshoot').show()
                    detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)

        QtWidgets.QApplication.processEvents()

        return actuator_modules, detector_modules

    pyqtSlot(bool)

    def stop_moves(self, overshoot):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_Motion
        """
        self.overshoot = overshoot
        for mod in self.actuator_modules:
            mod.stop_Motion()

    def set_default_preset(self):
        actuators = self.model_class.actuators
        actuator_names = self.model_class.actuators_name

        detectors_type = self.model_class.detectors_type
        detectors = self.model_class.detectors
        detectors_name = self.model_class.detectors_name

        detector_modules = []
        for ind_det, det in enumerate(detectors):
            detector_modules.append(DAQ_Viewer(area, title=detectors_name[ind_det], DAQ_type=detectors_type[ind_det]))
            # self.detector_modules[-1].ui.IniDet_pb.click()
            QtWidgets.QApplication.processEvents()
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(detectors[ind_det])
            detector_modules[-1].ui.Quit_pb.setEnabled(False)

        self.dock_area.addDock(self.dock_output, 'bottom')
        self.dock_area.moveDock(self.dock_input, 'bottom', self.dock_output)
        self.dock_area.addDock(self.dock_pid, 'left')

        dock_moves = []
        actuator_modules = []
        for ind_act, act in enumerate(actuators):
            form = QtWidgets.QWidget()
            dock_moves.append(Dock(actuator_names[ind_act]))
            area.addDock(dock_moves[-1], 'bottom', self.dock_pid)
            dock_moves[-1].addWidget(form)
            actuator_modules.append(DAQ_Move(form))
            QtWidgets.QApplication.processEvents()
            actuator_modules[-1].ui.Stage_type_combo.setCurrentText(actuators[ind_act])
            actuator_modules[-1].ui.Quit_pb.setEnabled(False)
            # self.actuator_modules[-1].ui.IniStage_pb.click()
            # QThread.msleep(1000)
            QtWidgets.QApplication.processEvents()

        return actuator_modules, detector_modules

    def ini_model(self):
        try:
            model_name = self.settings.child('models', 'model_class').value()
            model = importlib.import_module('.' + model_name, self.model_mod.__name__ + '.models')
            self.model_class = getattr(model, model_name)(self)

            # try to get corresponding managers file
            filename = os.path.join(get_set_pid_path(), model_name + '.xml')
            if os.path.isfile(filename):
                self.actuator_modules, self.detector_modules = self.set_file_preset(model_name)
            else:
                self.actuator_modules, self.detector_modules = self.set_default_preset()

            # # connecting to logger
            # for mov in self.actuator_modules:
            #     mov.log_signal[str].connect(self.add_log)
            # for det in self.detector_modules:
            #     det.log_signal[str].connect(self.add_log)
            # self.log_signal[str].connect(self.add_log)

            self.model_class.ini_model()

            self.enable_controls_pid(True)
            self.model_led.set_as_true()
            self.ini_model_action.setEnabled(False)

        except Exception as e:
            self.update_status(getLineInfo() + str(e), log_type='log')

    def quit_fun(self):
        """
        """
        try:
            try:
                self.PIDThread.exit()
            except Exception as e:
                print(e)

            for module in self.actuator_modules:
                try:
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except Exception as e:
                    print(e)

            for module in self.detector_modules:
                try:
                    module.stop_all()
                    QtWidgets.QApplication.processEvents()
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
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

                elif param.name() == 'module_settings':
                    if param.value():
                        self.settings.sigTreeStateChanged.disconnect(self.parameter_tree_changed)
                        param.setValue(False)
                        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
                        self.preset_manager.set_PID_preset(self.settings.child('models', 'model_class').value())

                elif param.name() == 'refresh_plot_time' or param.name() == 'timeout':
                    self.command_pid.emit(ThreadCommand('update_timer', [param.name(), param.value()]))

                elif param.name() == 'set_point':
                    if self.pid_led.state:
                        self.command_pid.emit(ThreadCommand('update_options', dict(setpoint=param.value())))
                    else:
                        output = self.model_class.convert_output(param.value(), 0, stab=False)
                        for ind_act, act in enumerate(self.actuator_modules):
                            act.move_Abs(output[ind_act])

                elif param.name() == 'sample_time':
                    self.command_pid.emit(ThreadCommand('update_options', dict(sample_time=param.value())))

                elif param.name() in putils.iter_children(
                        self.settings.child('main_settings', 'pid_controls', 'output_limits'), []):
                    output_limits = [None, None]
                    if self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                           'output_limit_min_enabled').value():
                        output_limits[0] = self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                                               'output_limit_min').value()
                    if self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                           'output_limit_max_enabled').value():
                        output_limits[1] = self.settings.child('main_settings', 'pid_controls', 'output_limits',
                                                               'output_limit_max').value()

                    self.command_pid.emit(ThreadCommand('update_options', dict(output_limits=output_limits)))

                elif param.name() in putils.iter_children(
                        self.settings.child('main_settings', 'pid_controls', 'filter'), []):
                    self.command_pid.emit(ThreadCommand('update_filter',
                                                        [dict(
                                                            enable=self.settings.child('main_settings', 'pid_controls',
                                                                                       'filter',
                                                                                       'filter_enable').value(),
                                                            value=self.settings.child('main_settings', 'pid_controls',
                                                                                      'filter',
                                                                                      'filter_step').value())]))

                elif param.name() in putils.iter_children(
                        self.settings.child('main_settings', 'pid_controls', 'pid_constants'), []):
                    Kp = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kp').value()
                    Ki = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'ki').value()
                    Kd = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kd').value()
                    self.command_pid.emit(ThreadCommand('update_options', dict(tunings=(Kp, Ki, Kd))))

                elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
                    self.model_class.update_settings(param)

                elif param.name() == 'detector_modules':
                    self.model_class.update_detector_names()

            elif change == 'parent':
                pass

    @pyqtSlot(list)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """
            | General function to get datas/infos from all threads back to the main.
            |

            Switch the status with :
                * *"Update status"* : Update the status bar with the status attribute txt message

        """
        if status[0] == "Update_Status":
            self.update_status(status[1], log_type=status[2])


class PIDRunner(QObject):
    status_sig = pyqtSignal(list)
    pid_output_signal = pyqtSignal(dict)

    def __init__(self, model_class,
                 move_done_signals=[],
                 grab_done_signals=[],
                 move_modules_commands=[],
                 detector_modules_commands=[],
                 params=dict([]), filter=dict([]),
                 det_averaging=[]
                 ):
        """
        Init the PID instance with params as initial conditions

        Parameters
        ----------
        params: (dict) Kp=1.0, Ki=0.0, Kd=0.0,setpoint=0, sample_time=0.01, output_limits=(None, None),
                 auto_mode=True,
                 proportional_on_measurement=False)
        """
        super().__init__()
        self.model_class = model_class
        self.move_done_signals = move_done_signals
        self.grab_done_signals = grab_done_signals
        self.det_averaging = det_averaging
        self.move_modules_commands = move_modules_commands
        self.detector_modules_commands = detector_modules_commands

        self.current_time = 0
        self.input = 0
        self.output = None
        self.output_to_actuator = None
        self.output_limits = None, None
        self.filter = filter  # filter=dict(enable=self.settings.child('main_settings', 'filter',
        # 'filter_enable').value(), value=self.settings.child('main_settings', 'filter', 'filter_step').value())
        self.pid = PID(**params)  # #PID(object):
        self.pid.set_auto_mode(False)
        self.refreshing_ouput_time = 200
        self.running = True
        self.timer = self.startTimer(self.refreshing_ouput_time)
        self.det_done_datas = OrderedDict()
        self.move_done_positions = OrderedDict()
        self.move_done_flag = False
        self.det_done_flag = False
        self.paused = True
        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.setInterval(10000)
        self.timeout_scan_flag = False
        self.timeout_timer.timeout.connect(self.timeout)

    def timerEvent(self, event):
        if self.output_to_actuator is not None:
            self.pid_output_signal.emit(dict(output=self.output_to_actuator, input=[self.input]))
        else:
            self.pid_output_signal.emit(dict(output=[0], input=[self.input]))

    def timeout(self):
        self.status_sig.emit(["Update_Status", 'Timeout occured', 'log'])
        self.timeout_scan_flag = True

    def wait_for_det_done(self):
        self.timeout_scan_flag = False
        self.timeout_timer.start()
        while not (self.det_done_flag or self.timeout_scan_flag):
            # wait for grab done signals to end
            QtWidgets.QApplication.processEvents()
        self.timeout_timer.stop()

    def wait_for_move_done(self):
        self.timeout_scan_flag = False
        self.timeout_timer.start()
        while not (self.move_done_flag or self.timeout_scan_flag):
            # wait for move done signals to end
            QtWidgets.QApplication.processEvents()
        self.timeout_timer.stop()

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

        elif command.command == 'input':
            self.update_input(*command.attributes)

        elif command.command == 'update_timer':
            if command.attributes[0] == 'refresh_plot_time':
                self.killTimer(self.timer)
                self.refreshing_ouput_time = command.attributes[1]
                self.timer = self.startTimer(self.refreshing_ouput_time)
            elif command.attributes[0] == 'timeout':
                self.timeout_timer.setInterval(command.attributes[1])

        elif command.command == 'update_filter':
            self.filter = command.attributes[0]

        # elif command.command == "move_Abs":
        #     self.set_option(dict(setpoint=command.attributes[0]))

    def update_input(self, measurements):
        self.input = self.model_class.convert_input(measurements)

    def start_PID(self, input=None):
        try:
            for sig in self.move_done_signals:
                sig.connect(self.move_done)
            for sig in self.grab_done_signals:
                sig.connect(self.det_done)

            self.current_time = time.perf_counter()
            self.status_sig.emit(["Update_Status", 'PID loop starting', 'log'])
            while self.running:
                # print('input: {}'.format(self.input))
                # # GRAB DATA FIRST AND WAIT ALL DETECTORS RETURNED

                self.det_done_flag = False
                self.det_done_datas = OrderedDict()
                for ind_det, cmd in enumerate(self.detector_modules_commands):
                    cmd.emit(ThreadCommand("single",
                                           [self.det_averaging[ind_det]]))
                    QtWidgets.QApplication.processEvents()
                self.wait_for_det_done()

                self.input = self.model_class.convert_input(self.det_done_datas)

                # # EXECUTE THE PID
                output = self.pid(self.input)

                # # PROCESS THE OUTPUT IF NEEDED
                if output is not None and self.output is not None:
                    if self.filter['enable']:
                        if np.abs(output - self.output) <= self.filter['value']:
                            self.output = output
                        else:
                            self.output += np.abs(self.filter['value']) * np.sign(output - self.output)
                            self.pid._last_output = self.output
                    else:
                        self.output = output
                else:
                    self.output = output

                # # APPLY THE PID OUTPUT TO THE ACTUATORS
                # print('output: {}'.format(self.output))

                if self.output is None:
                    self.output = self.pid.setpoint

                dt = time.perf_counter() - self.current_time
                self.output_to_actuator = self.model_class.convert_output(self.output, dt, stab=True)

                if not self.paused:
                    self.move_done_positions = OrderedDict()
                    for ind_mov, cmd in enumerate(self.move_modules_commands):
                        cmd.emit(ThreadCommand('move_Abs', [self.output_to_actuator[ind_mov]]))
                        QtWidgets.QApplication.processEvents()
                    self.wait_for_move_done()

                self.current_time = time.perf_counter()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(int(self.pid.sample_time * 1000))

            self.status_sig.emit(["Update_Status", 'PID loop exiting', 'log'])
            for sig in self.move_done_signals:
                sig.disconnect(self.move_done)
            for sig in self.grab_done_signals:
                sig.disconnect(self.det_done)
        except Exception as e:
            self.status_sig.emit(["Update_Status", str(e), 'log'])

    pyqtSlot(OrderedDict)  # OrderedDict(name=self.title,data0D=None,data1D=None,data2D=None)

    def det_done(self, data):
        """
        """
        try:
            if data['name'] not in list(self.det_done_datas.keys()):
                self.det_done_datas[data['name']] = data
            if len(self.det_done_datas.items()) == len(self.grab_done_signals):
                self.det_done_flag = True
        except Exception as e:
            self.status_sig.emit(["Update_Status", str(e), 'log'])

    pyqtSlot(str, float)

    def move_done(self, name, position):
        """
            | Update the move_done_positions attribute if needed.
            | If position attribute is setted, for all move modules launched, update scan_read_positions with a [modulename, position] list.

            ============== ============ =================
            **Parameters**    **Type**    **Description**
            *name*            string     the module name
            *position*        float      ???
            ============== ============ =================
        """
        try:
            if name not in list(self.move_done_positions.keys()):
                self.move_done_positions[name] = position

            if len(self.move_done_positions.items()) == len(self.move_done_signals):
                self.move_done_flag = True

        except Exception as e:
            self.status_sig.emit(["Update_Status", str(e), 'log'])

    def set_option(self, **option):
        for key in option:
            if hasattr(self.pid, key):
                if key == 'sample_time':
                    setattr(self.pid, key, option[key] / 1000)
                else:
                    setattr(self.pid, key, option[key])
            if key == 'setpoint' and not self.pid.auto_mode:
                dt = time.perf_counter() - self.current_time
                self.output = option[key]
                self.output_to_actuator = self.model_class.convert_output(self.output, dt, stab=False)

                for ind_move, cmd in enumerate(self.move_modules_commands):
                    cmd.emit(ThreadCommand('move_Abs', [self.output_to_actuator[ind_move]]))
                self.current_time = time.perf_counter()
            if key == 'output_limits':
                self.output_limits = option[key]

    def run_PID(self, last_value):
        self.status_sig.emit(["Update_Status", 'Stabilization started', 'log'])
        self.running = True
        self.pid.set_auto_mode(True, last_value)

    def pause_PID(self, pause_state):
        if pause_state:
            self.pid.set_auto_mode(False, self.output)
            self.status_sig.emit(["Update_Status", 'Stabilization paused', 'log'])
        else:
            self.pid.set_auto_mode(True, self.output)
            self.status_sig.emit(["Update_Status", 'Stabilization restarted from pause', 'log'])
        self.paused = pause_state

    def stop_PID(self):
        self.running = False
        self.status_sig.emit(["Update_Status", 'PID loop exiting', 'log'])


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()

    win.setCentralWidget(area)
    # win.resize(1000,500)
    win.setWindowTitle('pymodaq PID')

    # viewer1 = DAQ_Viewer(area, title="Testing2D", DAQ_type='DAQ2D')
    # viewer1.ui.IniDet_pb.click()
    # #QThread.msleep(1000)
    # QtWidgets.QApplication.processEvents()
    # viewer1.settings.child('main_settings','wait_time').setValue(100)
    #
    # viewer2 = DAQ_Viewer(area, title="Testing 1D", DAQ_type='DAQ1D')
    # viewer2.ui.IniDet_pb.click()
    # #QThread.msleep(1000)
    # QtWidgets.QApplication.processEvents()
    # viewer2.settings.child('main_settings', 'wait_time').setValue(100)
    #
    # Form = QtWidgets.QWidget()
    # dock_move = Dock('Move')
    # area.addDock(dock_move)
    # dock_move.addWidget(Form)
    # move = DAQ_Move(Form)
    # move.ui.IniStage_pb.click()
    # #QThread.msleep(1000)
    # QtWidgets.QApplication.processEvents()

    prog = DAQ_PID(area, [], [])
    win.show()
    sys.exit(app.exec_())
