import os
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QRectF
import logging

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.daq_utils import DockArea
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils.manage_preset import PresetManager
from pyqtgraph.dockarea import Dock
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_param_from_param, get_set_pid_path, getLineInfo, get_set_local_dir, get_set_log_path
import importlib
from simple_pid import PID
import time
import datetime
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_move.daq_move_main import DAQ_Move
import numpy as np
from collections import OrderedDict

local_path = get_set_local_dir()
log_path = get_set_log_path()


class DAQ_PID(QObject):
    """
    """
    log_signal = pyqtSignal(str)
    #look for eventual model files
    command_pid = pyqtSignal(ThreadCommand)
    models = []
    try:
        model_mod = importlib.import_module('pymodaq_pid_models')
        for ind_file, entry in enumerate(os.scandir(os.path.join(model_mod.__path__[0], 'models'))):
            if not entry.is_dir() and entry.name != '__init__.py':
                try:
                    file, ext = os.path.splitext(entry.name)
                    importlib.import_module('.'+file, model_mod.__name__+'.models')

                    models.append(file)
                except Exception as e:
                    print(e)
        if 'PIDModelMock' in models:
            mods = models
            mods.pop(models.index('PIDModelMock'))
            models = ['PIDModelMock']
            models.extend(mods)

    except Exception as e:
        print(e)

    if len(models) == 0:
        raise Exception('No valid installed models')

    params = [
        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True, 'children': [
            {'title': 'Models class:', 'name': 'model_class', 'type': 'str', 'value': models[0]},
            {'title': 'Preset module settings:', 'name': 'module_settings', 'type': 'bool', 'value': False},
            {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},
        ]},
        {'title': 'Main Settings:','name': 'main_settings', 'expanded': True, 'type': 'group','children':[
            {'title': 'Update modules:', 'name': 'update_modules', 'type': 'bool', 'value': False},
            {'title': 'Measurement modules:', 'name': 'detector_modules', 'type': 'itemselect'},
            {'title': 'Actuator modules:', 'name': 'actuator_modules', 'type': 'itemselect'},
            {'title': 'Acquisition Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000},
            {'title': 'PID controls:', 'name': 'pid_controls', 'type': 'group','children': [
                {'title': 'Set Point:', 'name': 'set_point', 'type': 'float', 'value': 0., ',readonly': True},
                {'title': 'Sample time (ms):', 'name': 'sample_time', 'type': 'int', 'value': 10},
                {'title': 'Refresh plot time (ms):', 'name': 'refresh_plot_time', 'type': 'int', 'value': 200},
                {'title': 'Output limits:', 'name': 'output_limits', 'expanded': True, 'type': 'group', 'children': [
                    {'title': 'Output limit (min):', 'name': 'output_limit_min_enabled', 'type': 'bool','value': False},
                    {'title': 'Output limit (min):', 'name': 'output_limit_min', 'type': 'float', 'value': 0},
                    {'title': 'Output limit (max):', 'name': 'output_limit_max_enabled', 'type': 'bool', 'value': False},
                    {'title': 'Output limit (max:', 'name': 'output_limit_max', 'type': 'float', 'value': 100},
                    ]},
                {'title': 'Filter:', 'name': 'filter', 'expanded': True, 'type': 'group', 'children': [
                    {'title': 'Enable filter:', 'name': 'filter_enable', 'type': 'bool', 'value': False},
                    {'title': 'Filter step:', 'name': 'filter_step', 'type': 'float', 'value': 0, 'min':0},
                ]},
                {'title': 'Auto mode:', 'name': 'auto_mode', 'type': 'bool', 'value': False, 'readonly': True},
                {'title': 'Prop. on measurement:', 'name': 'proportional_on_measurement', 'type': 'bool', 'value': False},
                {'title': 'PID constants:', 'name': 'pid_constants', 'type': 'group', 'children': [
                    {'title': 'Kp:', 'name': 'kp', 'type': 'float', 'value': 2, 'min': 0},
                    {'title': 'Ki:', 'name': 'ki', 'type': 'float', 'value': 0.1, 'min': 0},
                    {'title': 'Kd:', 'name': 'kd', 'type': 'float', 'value': 0.01, 'min': 0},
                    ]},

            ]},

        ]},



        ]

    def __init__(self,area, detector_modules = [], actuator_modules =[]):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_PID,self).__init__()
        self.settings = Parameter.create(title='PID settings', name='pid_settings', type='group', children=self.params)

        self.model_class = None
        self.detector_modules = detector_modules
        self.actuator_modules = actuator_modules
        self.dock_area = area
        self.overshoot = None
        self.preset_manager = PresetManager()
        self.setupUI()
        self.enable_controls_pid(False)

        self.enable_controls_pid_run(False)

    def ini_PID(self):

        if self.ini_PID_action.isChecked():
            output_limits =[None,None]
            if self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_min_enabled').value():
                output_limits[0] = self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_min').value()
            if self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_max_enabled').value():
                output_limits[1] = self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_max').value()

            used_actuators =[]
            selected_actuators = self.settings.child('main_settings', 'actuator_modules').value()['selected']
            if not isinstance(selected_actuators, list):
                selected_actuators = [selected_actuators]


            actuators_names = [mod.title for mod in self.actuator_modules]
            for mod in selected_actuators:
                used_actuators.append(self.actuator_modules[actuators_names.index(mod)])


            if len(used_actuators) == 0:
                msgBox = QtWidgets.QMessageBox(parent=None)
                msgBox.setWindowTitle("Error")
                msgBox.setText('No actuators selected')
                ret = msgBox.exec()
                return

            used_dets =[]
            selected_dets = self.settings.child('main_settings', 'detector_modules').value()['selected']
            if not isinstance(selected_dets, list):
                selected_dets = [selected_dets]
            det_names = [mod.split('//')[0] for mod in selected_dets]
            det_titles = [mod.title for mod in self.detector_modules]
            for mod in det_names:
                used_dets.append(self.detector_modules[det_titles.index(mod)])
            used_dets = list(set(used_dets))  #get single instance of a given detector

            if len(used_dets) == 0:
                msgBox = QtWidgets.QMessageBox(parent=None)
                msgBox.setWindowTitle("Error")
                msgBox.setText('No detectors selected')
                ret = msgBox.exec()
                return


            self.PIDThread = QThread()
            pid_runner = PIDRunner(self.model_class, selected_dets, used_actuators, used_dets,
                       dict(Kp=self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kp').value(),
                            Ki=self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'ki').value(),
                            Kd=self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kd').value(),
                            setpoint=self.settings.child('main_settings', 'pid_controls', 'set_point').value(),
                            sample_time=self.settings.child('main_settings', 'pid_controls', 'sample_time').value()/1000,
                            output_limits=output_limits,
                            auto_mode=False),
                            filter=dict(enable=self.settings.child('main_settings', 'pid_controls', 'filter', 'filter_enable').value(),
                                         value=self.settings.child('main_settings', 'pid_controls', 'filter', 'filter_step').value()))

            # for det_sig in det_grab_done:
            #     det_sig.connect(pid_runner.update_input)


            self.PIDThread.pid_runner = pid_runner
            pid_runner.pid_output_signal.connect(self.process_output)
            pid_runner.status_sig.connect(self.thread_status)
            self.command_pid.connect(pid_runner.queue_command)
            #pid_runner.moveToThread(self.PIDThread)

            self.PIDThread.start()
            self.pid_led.set_as_true()
            self.enable_controls_pid_run(True)



        else:
            if hasattr(self,'PIDThread'):
                if self.PIDThread.isRunning():
                    try:
                        self.PIDThread.quit()
                    except:
                        pass
            self.pid_led.set_as_false()
            self.enable_controls_pid_run(False)

    pyqtSlot(dict)
    def process_output(self, datas):
        self.output_viewer.show_data([[dat] for dat in datas['output']])
        self.input_viewer.show_data([[dat] for dat in datas['input']])

    def enable_controls_pid(self,enable = False):
        self.ini_PID_action.setEnabled(enable)
        self.setpoint_sb.setOpts(enabled = enable)

    def enable_controls_pid_run(self,enable = False):
        self.run_action.setEnabled(enable)
        self.pause_action.setEnabled(enable)


    def setupUI(self):

        self.dock_pid = Dock('PID controller', area)
        area.addDock(self.dock_pid)

        #%% create logger dock
        self.logger_dock=Dock("Logger")
        self.logger_list=QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.logger_dock.addWidget(self.logger_list)
        self.dock_area.addDock(self.logger_dock,'right')
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
        toolbar_layout.addWidget(self.quit_action,0,0,1,2)
        self.quit_action.clicked.connect(self.quit_fun)

        model_label = QtWidgets.QLabel('Models:')
        self.models_combo = QtWidgets.QComboBox()
        self.models_combo.addItems(self.models)
        self.models_combo.currentTextChanged.connect(self.model_changed)
        toolbar_layout.addWidget(model_label, 1, 0)
        toolbar_layout.addWidget(self.models_combo, 1,1,1,3)


        iconini = QtGui.QIcon()
        iconini.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/ini.png"), QtGui.QIcon.Normal,
                          QtGui.QIcon.Off)
        self.ini_model_action = QtWidgets.QPushButton(iconini, "Init Model")
        self.ini_model_action.setToolTip('Initialize the chosen model')
        toolbar_layout.addWidget(self.ini_model_action,2,0)
        self.ini_model_action.clicked.connect(self.ini_model)
        self.model_led = QLED()
        toolbar_layout.addWidget(self.model_led, 2,1)

        self.ini_PID_action = QtWidgets.QPushButton(iconini, "Init PID")
        self.ini_PID_action.setToolTip('Initialize the PID loop')
        toolbar_layout.addWidget(self.ini_PID_action,2,2)
        self.ini_PID_action.setCheckable(True)
        self.ini_PID_action.clicked.connect(self.ini_PID)
        self.pid_led = QLED()
        toolbar_layout.addWidget(self.pid_led, 2,3)

        self.iconrun = QtGui.QIcon()
        self.iconrun.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.icon_stop = QtGui.QIcon()
        self.icon_stop.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/stop.png"))
        self.run_action = QtWidgets.QPushButton(self.iconrun, "", None)
        self.run_action.setToolTip('Start PID loop')
        self.run_action.setCheckable(True)
        toolbar_layout.addWidget(self.run_action,0,2)
        self.run_action.clicked.connect(self.run_PID)


        iconpause = QtGui.QIcon()
        iconpause.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/pause.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.pause_action = QtWidgets.QPushButton(iconpause, "", None)
        self.pause_action.setToolTip('Pause PID')
        self.pause_action.setCheckable(True)
        toolbar_layout.addWidget(self.pause_action,0,3)
        self.pause_action.setChecked(True)
        self.pause_action.clicked.connect(self.pause_PID)

        lab = QtWidgets.QLabel('Set Point:')
        toolbar_layout.addWidget(lab, 3,0,1,2)

        self.setpoint_sb = custom_tree.SpinBoxCustom()
        toolbar_layout.addWidget(self.setpoint_sb,3,2,1,2)
        self.setpoint_sb.valueChanged.connect(self.settings.child('main_settings', 'pid_controls', 'set_point').setValue)

        #create main parameter tree
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
        self.dock_area.addDock(self.dock_input, 'bottom',self.dock_output)

        if len(self.models) != 0:
            self.get_set_model_params(self.models[0])


        self.get_set_measurement_datas()

        #connecting from tree
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector
        self.dock_pid.addWidget(widget)

    def get_set_model_params(self, model_file):
        self.settings.child('models', 'model_params').clearChildren()
        model = importlib.import_module('.' + model_file, self.model_mod.__name__+'.models')
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

    def update_status(self,txt,log_type=None):
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
    def add_log(self,txt):
        """
            Add the QListWisgetItem initialized with txt informations to the User Interface logger_list and to the save_parameters.logger array.

            =============== =========== ======================
            **Parameters**    **Type**   **Description**
            *txt*             string     the log info to add.
            =============== =========== ======================
        """
        try:
            now=datetime.datetime.now()
            new_item=QtWidgets.QListWidgetItem(now.strftime('%Y/%m/%d %H:%M:%S')+": "+txt)
            self.logger_list.addItem(new_item)
        except:
            pass

    def set_file_preset(self,model):
        """
            Set a file preset from the converted xml file given by the filename parameter.


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


        #################################################################
        ###### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins=[{'type': 'move', 'value': child} for child in self.preset_manager.preset_params.child(('Moves')).children()]+[{'type': 'det', 'value': child} for child in self.preset_manager.preset_params.child(('Detectors')).children()]

        for plug in plugins:
            plug['ID']=plug['value'].child('params','main_settings','controller_ID').value()
            if plug["type"]=='det':
                plug['status']=plug['value'].child('params','detector_settings','controller_status').value()
            else:
                plug['status']=plug['value'].child('params','move_settings', 'multiaxes', 'multi_status').value()

        IDs=list(set([plug['ID'] for plug in plugins]))
        #%%
        plugins_sorted=[]
        for id in IDs:
            plug_Ids=[]
            for plug in plugins:
                if plug['ID']==id:
                    plug_Ids.append(plug)
            plug_Ids.sort(key=lambda status: status['status'])
            plugins_sorted.append(plug_Ids)
        #################################################################
        #######################

        ind_move=-1
        ind_det=-1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):


                plug_name=plugin['value'].child(('name')).value()
                plug_init=plugin['value'].child(('init')).value()
                plug_settings=plugin['value'].child(('params'))

                if plugin['type'] == 'move':
                    ind_move+=1
                    plug_type=plug_settings.child('main_settings','move_type').value()
                    self.move_docks.append(Dock(plug_name, size=(150,250)))
                    if ind_move==0:
                        self.dock_area.addDock(self.move_docks[-1], 'top',self.logger_dock)
                    else:
                        self.dock_area.addDock(self.move_docks[-1], 'above',self.move_docks[-2])
                    move_forms.append(QtWidgets.QWidget())
                    mov_mod_tmp=DAQ_Move(move_forms[-1],plug_name)

                    mov_mod_tmp.ui.Stage_type_combo.setCurrentText(plug_type)
                    mov_mod_tmp.ui.Quit_pb.setEnabled(False)
                    QtWidgets.QApplication.processEvents()

                    set_param_from_param(mov_mod_tmp.settings,plug_settings)
                    QtWidgets.QApplication.processEvents()

                    mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
                    self.move_docks[-1].addWidget(move_forms[-1])
                    actuator_modules.append(mov_mod_tmp)

                    try:
                        if ind_plugin==0: #should be a master type plugin
                            if plugin['status']!="Master":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                actuator_modules[-1].ui.IniStage_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_type:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                                master_controller=actuator_modules[-1].controller
                        else:
                            if plugin['status']!="Slave":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                actuator_modules[-1].controller=master_controller
                                actuator_modules[-1].ui.IniStage_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_type:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                    except Exception as e:
                        self.update_status(getLineInfo()+ str(e),'log')


                else:
                    ind_det+=1
                    plug_type=plug_settings.child('main_settings','DAQ_type').value()
                    plug_subtype=plug_settings.child('main_settings','detector_type').value()

                    self.det_docks_settings.append(Dock(plug_name+" settings", size=(150,250)))
                    self.det_docks_viewer.append(Dock(plug_name+" viewer", size=(350,350)))

                    if ind_det==0:
                        self.logger_dock.area.addDock(self.det_docks_settings[-1], 'bottom', self.dock_input) #dock_area of the logger dock
                    else:
                        self.dock_area.addDock(self.det_docks_settings[-1], 'bottom',self.det_docks_settings[-2])
                    self.dock_area.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])

                    det_mod_tmp=DAQ_Viewer(self.dock_area,dock_settings=self.det_docks_settings[-1],
                                                        dock_viewer=self.det_docks_viewer[-1],title=plug_name,
                                           DAQ_type=plug_type, parent_scan=self)
                    detector_modules.append(det_mod_tmp)
                    detector_modules[-1].ui.Detector_type_combo.setCurrentText(plug_subtype)
                    detector_modules[-1].ui.Quit_pb.setEnabled(False)
                    set_param_from_param(det_mod_tmp.settings,plug_settings)
                    QtWidgets.QApplication.processEvents()


                    try:
                        if ind_plugin==0: #should be a master type plugin
                            if plugin['status']!="Master":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                detector_modules[-1].ui.IniDet_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_subtype:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                                master_controller=detector_modules[-1].controller
                        else:
                            if plugin['status']!="Slave":
                                raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                            if plug_init:
                                detector_modules[-1].controller=master_controller
                                detector_modules[-1].ui.IniDet_pb.click()
                                QtWidgets.QApplication.processEvents()
                                if 'Mock' in plug_subtype:
                                    QThread.msleep(500)
                                else:
                                    QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                QtWidgets.QApplication.processEvents()
                    except Exception as e:
                        self.update_status(getLineInfo()+ str(e),'log')

                    detector_modules[-1].settings.child('main_settings','overshoot').show()
                    detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)

        QtWidgets.QApplication.processEvents()

        return actuator_modules,detector_modules


    pyqtSlot(bool)
    def stop_moves(self,overshoot):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_Motion
        """
        self.overshoot = overshoot
        self.stop_scan()
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
            #self.detector_modules[-1].ui.IniDet_pb.click()
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
            #self.actuator_modules[-1].ui.IniStage_pb.click()
            #QThread.msleep(1000)
            QtWidgets.QApplication.processEvents()

        return actuator_modules, detector_modules

    def ini_model(self):
        try:
            model_name = self.settings.child('models', 'model_class').value()
            model = importlib.import_module('.' +model_name, self.model_mod.__name__+'.models')
            self.model_class = getattr(model, model_name)(self)


            #try to get corresponding preset file
            filename = os.path.join(get_set_pid_path(), model_name + '.xml')
            if os.path.isfile(filename):
                self. actuator_modules,  self.detector_modules = self.set_file_preset(model_name)
            else:
                self.actuator_modules, self.detector_modules = self.set_default_preset()

            # connecting to logger
            for mov in self.actuator_modules:
                mov.log_signal[str].connect(self.add_log)
            for det in self.detector_modules:
                det.log_signal[str].connect(self.add_log)
            self.log_signal[str].connect(self.add_log)

            self.model_class.ini_model()

            self.get_set_measurement_datas()

            self.enable_controls_pid(True)
            self.model_led.set_as_true()
            self.ini_model_action.setEnabled(False)



        except Exception as e:
            self.update_status(str(e), log_type='log')

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

            areas=self.dock_area.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()

            self.dock_area.parent().close()

        except Exception as e:
            print(e)



    def get_set_measurement_datas(self):
        items_det = []
        preset_items_det = []
        for det in self.detector_modules:
            for key in det.data_to_save_export:
                if isinstance(det.data_to_save_export[key],dict):
                    for k in det.data_to_save_export[key]:
                        items_det.append(det.data_to_save_export['name']+'//'+key+'//'+k)
        if len(items_det) != 0:
            preset_items_det = [items_det[0]]
        self.settings.child('main_settings', 'detector_modules').setValue(dict(all_items=items_det, selected=preset_items_det))

        items_act=[]
        preset_items_act = []
        for act in self.actuator_modules:
            items_act.append(act.title)
        if len(items_act) != 0:
            preset_items_act = [items_act[0]]
        self.settings.child('main_settings', 'actuator_modules').setValue(dict(all_items=items_act, selected=preset_items_act))

    def model_changed(self, model):
        self.get_set_model_params(model)
        self.settings.child('models', 'model_class').setValue(model)


    def parameter_tree_changed(self,param,changes):
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

            See Also
            --------
            change_viewer, daq_utils.custom_parameter_tree.iter_children
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'module_settings':
                    self.preset_manager.set_PID_preset(self.settings.child('models','model_class').value())


                elif param.name() == 'update_modules':
                    if param.value():
                        self.get_set_measurement_datas()
                        QtWidgets.QApplication.processEvents()
                    param.setValue(False)

                elif param.name() == 'refresh_plot_time' or param.name() == 'timeout':
                    self.command_pid.emit(ThreadCommand('update_timer', [param.name(),param.value()]))

                elif param.name() == 'set_point':
                    if self.pid_led.state:
                        self.command_pid.emit(ThreadCommand('update_options', dict(setpoint=param.value())))
                    else:
                        output = self.model_class.convert_output(param.value(),0, stab=False)
                        for ind_act, act in enumerate(self.actuator_modules):
                            act.move_Abs(output[ind_act])


                elif param.name() == 'sample_time':
                    self.command_pid.emit(ThreadCommand('update_options', dict(sample_time=param.value())))

                elif param.name() in custom_tree.iter_children(self.settings.child('main_settings', 'pid_controls', 'output_limits'), []):
                    output_limits = [None, None]
                    if self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_min_enabled').value():
                        output_limits[0] = self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_min').value()
                    if self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_max_enabled').value():
                        output_limits[1] = self.settings.child('main_settings', 'pid_controls', 'output_limits', 'output_limit_max').value()

                    self.command_pid.emit(ThreadCommand('update_options', dict(output_limits=output_limits)))

                elif param.name() in custom_tree.iter_children(self.settings.child('main_settings', 'pid_controls', 'filter'), []):
                    self.command_pid.emit(ThreadCommand('update_filter',
                                    [dict(enable=self.settings.child('main_settings', 'pid_controls', 'filter', 'filter_enable').value(),
                                         value=self.settings.child('main_settings', 'pid_controls', 'filter', 'filter_step').value())]))

                elif param.name() in custom_tree.iter_children(self.settings.child('main_settings', 'pid_controls', 'pid_constants'), []):
                    Kp = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kp').value()
                    Ki = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'ki').value()
                    Kd = self.settings.child('main_settings', 'pid_controls', 'pid_constants', 'kd').value()
                    self.command_pid.emit(ThreadCommand('update_options', dict(tunings= (Kp, Ki, Kd))))

                elif param.name() in custom_tree.iter_children(self.settings.child('models', 'model_params'),[]):
                    self.model_class.update_settings(param)

                elif param.name() == 'detector_modules':
                    self.model_class.update_detector_names()

            elif change == 'parent':
                pass

    @pyqtSlot(list)
    def thread_status(self,status): # general function to get datas/infos from all threads back to the main
        """
            | General function to get datas/infos from all threads back to the main.
            |

            Switch the status with :
                * *"Update status"* : Update the status bar with the status attribute txt message

        """
        if status[0]=="Update_Status":
            self.update_status(status[1],log_type=status[2])



class PIDRunner(QObject):
    status_sig = pyqtSignal(list)
    pid_output_signal = pyqtSignal(dict)

    def __init__(self,model_class, selected_dets, used_actuators, used_dets, params, filter):
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
        self.selected_dets = selected_dets
        self.used_actuators = used_actuators
        self.used_dets = used_dets
        self.current_time = 0
        self.input = 0
        self.output = None
        self.output_to_actuator = None
        self.output_limits = None, None
        self.filter = filter #filter=dict(enable=self.settings.child('main_settings', 'filter', 'filter_enable').value(),                                         value=self.settings.child('main_settings', 'filter', 'filter_step').value())
        self.pid = PID(**params) ##PID(object):
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
        self.timeout_scan_flag=False
        self.timeout_timer.start()
        while not(self.det_done_flag or  self.timeout_scan_flag):
            #wait for grab done signals to end
            QtWidgets.QApplication.processEvents()
        self.timeout_timer.stop()

    def wait_for_move_done(self):
        self.timeout_scan_flag=False
        self.timeout_timer.start()
        while not(self.move_done_flag or  self.timeout_scan_flag):
            #wait for move done signals to end
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
            elif command.attributes[0] =='timeout':
                self.timeout_timer.setInterval(command.attributes[1])


        elif command.command == 'update_filter':
            self.filter = command.attributes[0]


    def update_input(self, measurements):
        self.input =self.model_class.convert_input(measurements)

    def start_PID(self, input = None):
        try:
            for mod in self.used_actuators:
                mod.move_done_signal.connect(self.move_done)
            for mod in self.used_dets:
                mod.grab_done_signal.connect(self.det_done)


            self.current_time = time.perf_counter()
            self.status_sig.emit(["Update_Status", 'PID loop starting', 'log'])
            while self.running:
                #print('input: {}'.format(self.input))
                ## GRAB DATA FIRST AND WAIT ALL DETECTORS RETURNED

                self.det_done_flag = False
                self.det_done_datas = OrderedDict()
                for det in self.used_dets:
                    det.grab_data()
                    QtWidgets.QApplication.processEvents()
                self.wait_for_det_done()

                self.input = self.model_class.convert_input(self.det_done_datas)

                ## EXECUTE THE PID
                output = self.pid(self.input)

                ## PROCESS THE OUTPUT IF NEEDED
                if output is not None and self.output is not None:
                    if self.filter['enable']:
                        if np.abs(output-self.output) <= self.filter['value']:
                            self.output = output
                        else:
                            self.output += np.abs(self.filter['value'])*np.sign(output - self.output)
                            self.pid._last_output = self.output
                    else:
                        self.output = output
                else:
                    self.output = output

                ## APPLY THE PID OUTPUT TO THE ACTUATORS
                #print('output: {}'.format(self.output))

                if self.output is None:
                    self.output = self.pid.setpoint


                dt = time.perf_counter() - self.current_time
                self.output_to_actuator = self.model_class.convert_output(self.output, dt, stab=True)

                if not self.paused:
                    self.move_done_positions = OrderedDict()
                    for ind_mov, mov in enumerate(self.used_actuators):
                        mov.move_Abs(self.output_to_actuator[ind_mov])
                        QtWidgets.QApplication.processEvents()
                    self.wait_for_move_done()

                self.current_time = time.perf_counter()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(self.pid.sample_time*1000)

            self.status_sig.emit(["Update_Status", 'PID loop exiting', 'log'])
            for mod in self.used_actuators:
                mod.move_done_signal.disconnect(self.move_done)
            for mod in self.used_dets:
                mod.grab_done_signal.disconnect(self.det_done)
        except Exception as e:
            self.status_sig.emit(["Update_Status", str(e), 'log'])

    pyqtSlot(OrderedDict) #OrderedDict(name=self.title,data0D=None,data1D=None,data2D=None)
    def det_done(self,data):
        """
        """
        try:
            if data['name'] not in list(self.det_done_datas.keys()):
                self.det_done_datas[data['name']]=data
            if len(self.det_done_datas.items())==len(self.used_dets):
                self.det_done_flag=True
        except Exception as e:
            self.status_sig.emit(["Update_Status", str(e), 'log'])


    pyqtSlot(str,float)
    def move_done(self,name,position):
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
                self.move_done_positions[name]=position

            if len(self.move_done_positions.items())==len(self.used_actuators):
                self.move_done_flag=True

        except Exception as e:
            self.status_sig.emit(["Update_Status",str(e),'log'])

    def set_option(self,**option):
        for key in option:
            if hasattr(self.pid, key):
                if key == 'sample_time':
                    setattr(self.pid, key, option[key]/1000)
                else:
                    setattr(self.pid,key, option[key])
            if key == 'setpoint' and not self.pid.auto_mode:
                dt = time.perf_counter() - self.current_time
                self.output = option[key]
                self.output_to_actuator = self.model_class.convert_output(self.output, dt, stab=False)

                for ind_move, mov in enumerate(self.used_actuators):
                    mov.move_Abs(self.output_to_actuator[ind_move])
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
    #win.resize(1000,500)
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
