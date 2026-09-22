from time import perf_counter
from typing import Iterable, TYPE_CHECKING, Callable

import numpy as np
from qtpy import QtWidgets, QtCore

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_data.h5modules.data_saving import DataBundle
from pymodaq_data import Q_
from pymodaq_data import DataToExport

from pymodaq_gui.utils.widgets import QLED
from pymodaq_gui.utils.app_worker import ExtensionWorker, SaverWorker
from pymodaq_gui import utils as gutils
from pymodaq_gui.managers.h5manager import FileAction
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils import Dock, QSpinBox_ro
from pymodaq_gui.utils.custom_app import WorkFlowActions
from pymodaq_gui.utils.shared_ui import MenuToolbarNames

from pymodaq.control_modules.thread_commands import ControlToHardwareMove
from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules import ModuleType
from pymodaq.control_modules.enums import MoveType
from pymodaq.extensions.utils import CustomExt


from pymodaq.extensions.ramping.utilities.histograming import HistogramProcessor, H5Histogramming, InfoForHistogram
from pymodaq.extensions.ramping.utilities.module_saver import RampSaver, GROUP
from pymodaq.extensions.ramping.utilities.ramp_generator import RampGenerator


if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer


logger = set_logger(get_module_name(__file__))
config = GlobalConfig()

EXTENSION_NAME = 'Ramp'  # the name that will be displayed in the extension list in the
# dashboard
CLASS_NAME = 'RampExtension'  # this should be the name of your class defined below


class StatusBarManager:
    def __init__(self, app: 'RampExtension'):
        self.app = app

        self._running_led: QLED = None
        self._step_sb: QSpinBox_ro = None
        self._n_steps_sb: QSpinBox_ro = None

    @property
    def statusbar(self):
        return self.app.statusbar

    def set_permanent_status(self, status: str):
        self.app.set_permanent_status(status)

    def create_permanent_widgets(self):
        self._n_steps_sb = QSpinBox_ro()
        self._n_steps_sb.setToolTip('Total number of steps')

        self._step_sb = QSpinBox_ro()
        self._step_sb.setToolTip('Current actuator value')

        self._running_led = QLED()
        self._running_led.setToolTip('Ramping status: green (running), red (idle)')
        self._running_led.clickable = False
        self.statusbar.addPermanentWidget(self._step_sb)
        self.statusbar.addPermanentWidget(self._n_steps_sb)
        self.statusbar.addPermanentWidget(self._running_led)
        pass

    @property
    def is_ramping(self) -> bool:
        return self._running_led.get_state()

    @is_ramping.setter
    def is_ramping(self, is_ramping: bool):
        self._running_led.set_as(is_ramping)

    @property
    def n_steps(self):
        return self._n_steps_sb.value()

    @n_steps.setter
    def n_steps(self, nsteps: int):
        self._n_steps_sb.setValue(nsteps)

    def set_current_step(self, step_ind: float | Q_):
        if self._step_sb is not None:
            if isinstance(step_ind, Q_):
                self._step_sb.setOpts(value=step_ind.magnitude, suffix=step_ind.units)
            else:
                self._step_sb.setValue(step_ind)

    def set_step_units(self, units: str):
        if self._step_sb is not None:
           self._step_sb.setOpts(suffix=units, siPrefix=True)


class RampExtension(CustomExt):

    _h5_base_group_name = 'Ramp'
    show_h5file_statusbar_widgets = True
    show_workflow_actions = True

    params = ([
        {'title': 'Ramping Actuator:', 'name': 'actuator', 'type': 'list', },
        {'title': 'Detectors to save:', 'name': 'detectors', 'type': 'itemselect', 'checkbox': True},
        {'title': 'Actuators to save:', 'name': 'actuators', 'type': 'itemselect', 'checkbox': True},
        {'title': 'Refresh Grab:', 'name': 'refresh_grab', 'type': 'float', 'value': 200e-3, 'suffix': 's',
         'siPrefix': True},
        {'title': 'Refresh Plot:', 'name': 'refresh_plot', 'type': 'float', 'value': 1., 'suffix': 's',
         'siPrefix': True},
        {'title': 'Ramp:', 'name': 'ramp', 'type': 'group', 'children': [
            {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': 500.},
            {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': 560.},
            {'title': 'Duration:', 'name': 'duration', 'type': 'float', 'value': 20,
             'suffix': config('ramping', 'duration_units')[0], 'siPrefix': True,
             'readonly': config('ramping', 'ramp_setting')[0] != 'duration'},
            {'title': 'Velocity:', 'name': 'velocity', 'type': 'float', 'value': 0,
             'suffix': '', 'siPrefix': True,
             'readonly': config('ramping', 'ramp_setting')[0] != 'velocity'},
        ]},
        {'title': 'Use Steps:', 'name': 'use_steps', 'type': 'bool', 'value': True},
        {'title': 'Steps:', 'name': 'steps', 'type': 'group', 'children': [
            {'title': 'Time Step:', 'name': 'time_step', 'type': 'float', 'value': 500e-3, 'suffix': 's',
             'siPrefix': True},
            {'title': 'Nsteps:', 'name': 'nsteps', 'type': 'int', 'value': 1, 'readonly': True},
            {'title': 'Current Step:', 'name': 'step', 'type': 'float', 'value': 300.},
        ]},

        ] + SaverWorker.params + HistogramProcessor.params)


    def __init__(self, parent: gutils.DockArea, dashboard):
        self.ramping_worker = RampingWorker(self)
        self.status_manager = StatusBarManager(self)
        super().__init__(parent, dashboard, add_toolbar_break=False)



        self.ramp: RampGenerator = None



        self._actuator: 'DAQ_Move' = None

        self._module_and_data_saver = RampSaver(self)

        self.viewer = ViewerDispatcher(title='Histogram')
        self.h5_histogrammer = H5Histogramming(self.h5_manager, self.viewer)

        self.setup_ui()

        self.update_n_steps()
        self.update_velocity()

        self.enable_workflow_actions(False)
        self.h5_manager.connect_action(FileAction.LOAD,
                                       self.h5_manager.load_file,
                                       connect=False)
        self.h5_manager.connect_action(FileAction.LOAD,
                                       lambda: self.h5_manager.load_file(mode='r'))

        self.h5_manager.file_loaded_signal.connect(lambda: self.set_action_enabled('update_histogram', True))

        if self.experiment_manager.entry_applied:
            self.enable_workflow_actions(True, other_actions='ini_positions')

    @property
    def _size_hint(self) -> QtCore.QSize:
        """ property telling the optimal size for your application UI

        To be reimplemented
        """
        return QtCore.QSize(1200, 850)

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout
        """
        self.settings_dock = Dock('Settings')
        self.settings_dock.addWidget(self.settings_tree)
        self.saving_dock = Dock('Saving')
        self.saving_dock.addWidget(self.h5_manager.get_h5saver(create_new_file=False).settings_tree)

        self.histogramer_settings_dock = Dock('Histogram Settings')
        self.histogramer_settings_dock.addWidget(self.h5_histogrammer.settings_tree)
        self.histogramer_dock = Dock('Histogram')
        self.histogramer_dock.addWidget(self.viewer.dockarea)

        self.dockarea.addDock(self.settings_dock, 'left')
        self.dockarea.addDock(self.histogramer_settings_dock, 'right', self.settings_dock)
        self.dockarea.addDock(self.histogramer_dock, 'right', self.histogramer_settings_dock)
        self.dockarea.addDock(self.saving_dock, 'right', self.histogramer_dock)

        self.settings_dock.setStretch(0.25)
        self.saving_dock.setStretch(0.25)
        self.histogramer_settings_dock.setStretch(0.25)
        self.histogramer_dock.setStretch(2)

        self.saving_dock.setVisible(False)
        self.populate_status_bar()

    def populate_status_bar(self):
        super().populate_status_bar()
        self.status_manager.create_permanent_widgets()
        self.status_manager.set_permanent_status('Waiting for instructions')

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        super().do_things_after_experiment_set(experiment_name, show_dashboard)
        self.settings.child('actuator').setLimits(self.modules_manager.actuators_name)
        self.display_control_modules()
        self._module_and_data_saver = RampSaver(self)

        try:
            self.enable_workflow_actions(True, other_actions='ini_positions')
        except KeyError: #actions may not yet be activated
            pass

    def display_control_modules(self):
        selected = self.settings['detectors']['selected']
        self.settings['detectors'] = dict(all_items=self.modules_manager.detectors_name,
                                          selected=selected)
        actuators = self.modules_manager.actuators_name[:]
        selected = self.settings['actuators']['selected']
        if self.settings['actuator'] in actuators:
            actuators.remove(self.settings['actuator'])
        self.settings['actuators'] = dict(all_items=actuators,
                                          selected=selected)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)

    def do_things_after_ui_setup(self):
        self.create_dashboard_toolbar(add_break=False)

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        See Also
        --------
        ActionManager.add_action
        """
        self.add_action('ini_positions', 'Init Positions', 'arrows_input',
                        menu='actions',
                        toolbar=self.toolbar, tip='Go to Initial Ramp position')
        self.toolbar.addSeparator()
        self.add_action('update_histogram', 'UpdateHistogram', 'bar_chart',
                        tip='Update the histogram given its settings',
                        enabled=False,)

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action(WorkFlowActions.START, self.ramping_worker.start)
        self.connect_action(WorkFlowActions.STOP, self.ramping_worker.stop)
        self.connect_action(WorkFlowActions.PAUSE, self.ramping_worker.pause)

        self.connect_action('ini_positions', self.ramping_worker.go_to_ini_ramp)
        self.connect_action('update_histogram', self.h5_histogrammer.update_histogramer)

        self.connect_action(WorkFlowActions.LOG, lambda visible: self.histogramer_dock.setVisible(visible))
        self.connect_action(WorkFlowActions.LOG, lambda visible: self.histogramer_settings_dock.setVisible(visible))

    @property
    def actuators_name(self) -> Iterable[str]:
        return self.modules_manager.actuators_name

    @property
    def actuator(self) -> 'DAQ_Move':
        if self._actuator is None:
            self._actuator =  self.modules_manager.get_mod_from_name(
                self.settings['actuator'],
                mod=ModuleType.Actuator)
        return self._actuator

    def update_ramp_settings(self):
        if self.actuator is not None:
            self.settings.child('ramp', 'start').setOpts(suffix=self.actuator.units)
            self.settings.child('ramp', 'stop').setOpts(suffix=self.actuator.units)

            self.settings.child('steps',  'step').setOpts(suffix=self.actuator.units)
            self.status_manager.set_step_units(self.actuator.units)

    def value_changed(self, param):
        """ Actions to perform when one of the param's value in self.settings is changed from the
        user interface

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        if param.name() in ('duration', 'velocity', 'time_step'):
            self.update_n_steps()
        elif param.name() == 'actuator':
            self._actuator: 'DAQ_Move' = None
            self.display_control_modules()
            self.update_ramp_settings()
        elif param.name() == 'use_steps':
            self.settings.child('steps').show(param.value())
        if param.name() in ('start', 'stop', 'time_step'):
            if config('ramping', 'ramp_setting')[0] == 'duration':
                self.update_velocity()
            else:
                self.update_duration()
            self.update_n_steps()

    def q_from_param(self, param: Parameter | tuple[str, ...]) -> Q_:
        if not isinstance(param, Parameter):
            param = self.settings.child(*param)
        return Q_(param.value(), param.opts['suffix'])

    @property
    def duration_units(self) -> str:
        return config('ramping', 'duration_units')[0]

    def update_n_steps(self):
        self.settings['steps', 'nsteps'] = (self.q_from_param(('ramp', 'duration')) /
                                            self.q_from_param(('steps', 'time_step'))).to_reduced_units().magnitude
    def update_duration(self):
        if not np.allclose(self.settings['ramp', 'velocity'], 0):
            self.settings.child('ramp', 'velocity').setOpts(
                suffix=f'{self.actuator.units}/{self.duration_units}')
            self.settings['ramp', 'duration'] = (
                    (self.q_from_param(('ramp', 'stop')) -
                     self.q_from_param(('ramp', 'start'))) /
                    self.q_from_param(('ramp', 'velocity'))).m_as(self.duration_units)
            self.settings.child('ramp', 'duration').setOpts(suffix=self.duration_units)
        else:
            self.settings['ramp', 'duration'] = 0

    def update_velocity(self):
        if self.actuator is not None:
            self.settings.child('ramp', 'velocity').setOpts(
                suffix=f'{self.actuator.units}/{self.duration_units}')
            self.settings['ramp', 'velocity'] = (
                    (self.q_from_param(('ramp', 'stop')) -
                     self.q_from_param(('ramp', 'start'))) /
                    self.q_from_param(('ramp', 'duration'))).to(
                f'{self.actuator.units}/{self.duration_units}').magnitude

    def get_ramp(self) -> RampGenerator:
        return RampGenerator(self.q_from_param(('ramp', 'start')),
                             self.q_from_param(('ramp', 'stop')),
                             self.q_from_param(('ramp', 'duration')),)

    def _quit_fun(self):
        if self.ramping_worker.is_running:
            messagebox(title='Running',
                       text='The Ramping is running, first stop it')
            return False

        elif self.settings[SaverWorker.worker_setting_name, 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.ramping_worker.stop("User prompted a quit of the Application, Stopping the Acquisition")
            return False

        self.h5_manager.close_file()

        return True


class RampingWorker(ExtensionWorker):

    has_data_processor = True

    def __init__(self, ramper: RampExtension, parent=None):
        super().__init__(app=ramper, parent=parent)

        self.ramp_timer = QtCore.QTimer()
        self.ramp_timer.timeout.connect(self.update_ramp)

        self.total_ramp_timer = QtCore.QTimer()
        self.total_ramp_timer.timeout.connect(self.stop)

        self._start_time: Q_ = None
        self._paused_time: Q_ = None

        self.current_node: GROUP | str = None

        self._processor_worker_class = HistogramProcessor

    @property
    def processor_worker(self) -> HistogramProcessor:
        return self._processor_worker


    @property
    def h5_browser(self) -> H5Histogramming:
        return self.app.h5_histogrammer

    def _on_data_processed(self, dte: DataToExport):
        self.thread_manager.n_jobs[HistogramProcessor.name] += 1
        self.app.viewer.show_data(dte)
        if self._running:
            self.run_plot_timer()

    def run_plot_timer(self):
        QtCore.QTimer.singleShot(int(self.app.q_from_param(('refresh_plot',)).m_as('ms')), self.update_histogramer)

    @property
    def histo_settings(self) -> Parameter:
        return self.app.h5_histogrammer.settings

    def update_histogramer_settings(self):
        with self.histo_settings.treeChangeBlocker(keep=set()):
            self.histo_settings['h5info', 'h5path'] = str(self.h5_manager.h5saver.file_path)
            self.histo_settings['h5info', 'node_path'] = self.current_node.path
            self.histo_settings.child('histo', 'actuator').setLimits([self.actuator.title])

            self.histo_settings['histo', 'start'] = self.ramp.start.m_as(self.actuator.units)
            self.histo_settings['histo', 'stop'] = self.ramp.start.m_as(self.actuator.units)

            self.histo_settings['histo', 'actuators'] = dict(
                all_items=self.settings['actuators']['all_items'],
                selected=self.settings['actuators']['selected'])
            self.histo_settings['histo', 'detectors'] = dict(
                all_items=self.settings['detectors']['all_items'],
                selected=self.settings['detectors']['selected'])
            self.histo_settings['histo', 'autobin'] = True
        self.histo_settings.setOpts(enabled=False)

    def update_histogramer(self):
        info = InfoForHistogram(
            self.current_node.path,
            self.actuator.title,
            self.ramp.start.m_as(self.actuator.units),
            self.ramp.end.m_as(self.actuator.units),
            other_names=[act.title for act in self.actuators] + [det.title for det in self.detectors],
            bins='auto')

        self.processor_worker.data_to_process_signal.emit(info)


    @property
    def ramp(self) -> RampGenerator:
        return self.app.get_ramp()

    @property
    def app(self) -> RampExtension:
        return self._app

    @property
    def status_manager(self) -> StatusBarManager:
        return self.app.status_manager

    @property
    def actuator(self) -> 'DAQ_Move':
        return self.app.actuator

    @property
    def detectors(self) -> list['DAQ_Viewer']:
        detectors = []
        for detector in self.settings['detectors']['selected']:
            det = self.modules_manager.get_mod_from_name(detector,
                                                         mod=ModuleType.Detector)
            if det is not None:
                detectors.append(det)
        return detectors

    @property
    def actuators(self) -> Iterable['DAQ_Move']:
        actuators = []
        for actuator in self.settings['actuators']['selected']:
            act = self.modules_manager.get_mod_from_name(actuator,
                                                         mod=ModuleType.Actuator)
            if act is not None:
                actuators.append(act)
        return actuators

    def go_to_ini_ramp(self, callback: Callable = None) -> None:
        self.modules_manager.move_actuators_with_callback(
            DataToExport(self.actuator.title,
                         data=[DataActuator(self.actuator.title,
                                      data=self.app.q_from_param(('ramp', 'start')).magnitude,
                                      units=self.app.q_from_param(('ramp', 'start')).units, )]),
            mode=MoveType.ABS,
            callback=callback
        )


    def _start(self):
        self.status_manager.set_permanent_status('Moving to Init value')
        self._app.set_action_enabled('update_histogram', True)

        self.go_to_ini_ramp(callback=self._on_ini_ramp_done)
        self.app.histogramer_settings_dock.setEnabled(False)

    def _on_ini_ramp_done(self, dte: DataToExport):
        self.modules_manager.forget_callback(self._on_ini_ramp_done,
                                             module_type=ModuleType.Actuator,
                                             disconnect_modules=True)

        self.status_manager.set_permanent_status('Initializing Ramp')
        self.ini_things()
        self.connect_modules()
        self.status_manager.set_permanent_status('Started Ramping')
        self.run_ramp()

        if self.app.is_action_checked(WorkFlowActions.LOG):

            self.processor_worker.data_processed_signal.connect(self._on_data_processed)
            self.run_plot_timer()

    def ini_things(self):

        if self.settings['use_steps']:
            self.app.status_manager.n_steps = self.settings['steps', 'nsteps']
            self.ramp_timer.setInterval(
                int(self.app.q_from_param(('steps', 'time_step')).m_as('ms')))
        else:
            self.app.status_manager.n_steps = 1

        self.total_ramp_timer.setInterval(
            int(self.app.q_from_param(('ramp', 'duration')).m_as('ms')))
        self.total_ramp_timer.setSingleShot(True)

        if self.app.is_action_checked(WorkFlowActions.LOG):
            self.h5_manager.close_file()
            self.module_and_data_saver.h5saver = self.h5_manager.h5saver
            self.current_node = self.module_and_data_saver.get_set_node(new=True)

            self.update_histogramer_settings()

        for detector in self.detectors:
            detector.settings['main_settings', 'wait_time'] = self.app.q_from_param(('refresh_grab',)).m_as('ms')
        for actuator in self.actuators:
            actuator.settings['main_settings', 'refresh_timeout'] = self.app.q_from_param(('refresh_grab',)).m_as('ms')
        self.actuator.settings['main_settings', 'refresh_timeout'] = self.app.q_from_param(('refresh_grab',)).m_as('ms')

    def connect_modules(self):
        # connect data signals to the event loop of the worker thread
        for detector in self.detectors:
            detector.grab_done_signal.connect(self.send_data_to_saver)
        for actuator in self.actuators:
            actuator.current_value_signal.connect(self.send_data_to_saver)
        self.actuator.current_value_signal.connect(self.send_data_to_saver)

    def start_modules(self):
        for detector in self.detectors:
            detector.grab_data(True)
        for actuator in self.actuators:
            actuator.get_continuous_actuator_value(get_value=True)
        self.actuator.get_continuous_actuator_value(get_value=True)

    def disconnect_modules(self):
        for detector in self.detectors:
            try:
                detector.grab_done_signal.disconnect(self.send_data_to_saver)
            except TypeError:
                pass

        for actuator in self.actuators:
            try:
                actuator.current_value_signal.disconnect(self.send_data_to_saver)

            except TypeError:
                pass
        try:
            self.actuator.current_value_signal.disconnect(self.send_data_to_saver)
        except TypeError:
            pass

    def stop_modules(self):
        for detector in self.detectors:
            detector.grab_data(False)

        for actuator in self.actuators:
            actuator.get_continuous_actuator_value(get_value=False)

        self.actuator.get_continuous_actuator_value(get_value=False)

    def run_ramp(self):
        self.status_manager.is_ramping = True
        self._start_time = Q_(perf_counter(), 's')
        self.start_modules()

        if self.settings['use_steps']:
            self.ramp_timer.start()
            self.update_ramp()
        else:
            actuator_value = DataActuator(self.actuator.title,
                                          data=self.app.q_from_param(('ramp', 'stop')).magnitude,
                                          units=self.app.q_from_param(('ramp', 'stop')).units, )
            self.actuator.command_hardware.emit(
                ThreadCommand(ControlToHardwareMove.MOVE_ABS, [actuator_value, False]))

            self.total_ramp_timer.start()



        self.app.enable_workflow_actions(False, excepted=(WorkFlowActions.PAUSE,
                                                          WorkFlowActions.STOP,
                                                          WorkFlowActions.LOG))

    def update_ramp(self):
        if self._start_time is None:
            self._start_time = Q_(perf_counter(), 's')
        elapsed_time = Q_(perf_counter(), 's') - self._start_time

        step: Q_ = self.ramp(elapsed_time)
        step_magnitude = step.m_as(self.app.q_from_param(('steps', 'step')).units)
        self.settings['steps', 'step'] = step_magnitude
        self.status_manager.set_current_step(step)
        actuator_value = DataActuator(self.actuator.title,
                                      data=step.magnitude,
                                      units=step.units, )
        self.actuator.command_hardware.emit(
            ThreadCommand(ControlToHardwareMove.MOVE_ABS, [actuator_value, False]))

        if elapsed_time > self.app.q_from_param(('ramp', 'duration')):
            self.stop()

    def send_data_to_saver(self, dte: DataToExport | DataActuator):
        if self.app.is_action_checked(WorkFlowActions.LOG):
            if isinstance(dte, DataActuator):
                dte = DataToExport(dte.name, data=[dte])

            self.saver_worker.data_to_save_signal.emit(DataBundle(dte=dte))
            self.thread_manager.n_jobs[SaverWorker.name] += 1


    def _stop(self, msg: str = None):
        self.status_manager.is_ramping = False
        self.ramp_timer.stop()
        self.total_ramp_timer.stop()

        self.disconnect_modules()
        self.stop_modules()

        self._start_time = None
        self.status_manager.set_permanent_status('Stopped Ramping')


        if self.app.is_action_checked(WorkFlowActions.LOG):
            self.processor_worker.data_processed_signal.disconnect(self._on_data_processed)
            self.thread_manager.exit_worker_thread('histogramer')
            self._histogram_processor = None

    def _pause(self, do_pause=True):
        if do_pause:
            self.ramp_timer.stop()
            self._paused_time = Q_(perf_counter(), 's')
            self.disconnect_modules()
            self.status_manager.is_ramping = False
        else:
            self._start_time = Q_(perf_counter(), 's') - (self._paused_time - self._start_time)

            self.connect_modules()
            self.ramp_timer.start()
            self.status_manager.is_ramping = True

    def _on_workers_terminated(self):
        self.app.histogramer_settings_dock.setEnabled(True)
        self.h5_browser.update_settings_from_file(self.h5_manager.get_h5saver(mode='r').file_path)


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Custom Ext')

    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(False)

    win_ext, ext = create_extension(dashboard, RampExtension)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
