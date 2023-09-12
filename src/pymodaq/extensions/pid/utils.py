import importlib
import inspect
import pkgutil
import warnings
from pathlib import Path
from typing import Union, List

from pymodaq.utils.gui_utils.dock import DockArea
from pymodaq.utils.daq_utils import get_plugins
from pymodaq.utils.logger import get_module_name, set_logger
from pymodaq.utils.daq_utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq.utils.data import DataToExport, DataCalculated, DataActuator

logger = set_logger(get_module_name(__file__))

DAQ_Move_Stage_type = get_plugins('daq_move')
DAQ_0DViewer_Det_types = get_plugins('daq_0Dviewer')
DAQ_1DViewer_Det_types = get_plugins('daq_1Dviewer')
DAQ_2DViewer_Det_types = get_plugins('daq_2Dviewer')
DAQ_NDViewer_Det_types = get_plugins('daq_NDviewer')


class DataToActuatorPID(DataToExport):
    """ Particular case of a DataToExport adding one named parameter to indicate what kind of change should be applied
    to the actuators, absolute or relative

    Attributes
    ----------
    mode: str
        Adds an attribute called mode holding a string describing the type of change: relative or absolute

    Parameters
    ---------
    mode: str
        either 'rel' or 'abs' for a relative or absolute change of the actuator's values
    """

    def __init__(self, *args, mode='rel', **kwargs):
        if mode not in ['rel', 'abs']:
            warnings.warn('Incorrect mode for the actuators, switching to default relative mode: rel')
            mode = 'rel'
        kwargs.update({'mode': mode})
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f'{super().__repr__()}: {self.mode}'


class PIDModelGeneric:
    limits = dict(max=dict(state=False, value=1),
                  min=dict(state=False, value=0),)
    konstants = dict(kp=1, ki=0.1, kd=0.001)
    params = []

    Nsetpoints = 1
    setpoint_ini = [0. for ind in range(Nsetpoints)]
    setpoints_names = ['' for ind in range(Nsetpoints)]

    actuators_name = []
    detectors_name = []

    epsilon = 1

    def __init__(self, pid_controller):
        self.pid_controller = pid_controller  # instance of the pid_controller using this model
        self.modules_manager = pid_controller.modules_manager

        self.settings = self.pid_controller.settings.child('models', 'model_params')  # set of parameters
        self.data_names = None
        self.curr_output = [0. for ind in range(self.Nsetpoints)]
        self.curr_input = None

        self.check_modules(self.modules_manager)

    def setpoint(self, values):
        self.pid_controller.setpoints = values

    def apply_constants(self):
        for kxx in self.konstants:
            self.pid_controller.settings.child('main_settings', 'pid_controls', 'pid_constants',
                                               kxx).setValue(self.konstants[kxx])

    def apply_limits(self):
        for limit in self.limits:
            self.pid_controller.settings.child('main_settings', 'pid_controls', 'output_limits',
                                               f'output_limit_{limit}').setValue(self.limits[limit]['value'])
            self.pid_controller.settings.child('main_settings', 'pid_controls', 'output_limits',
                                               f'output_limit_{limit}_enabled').setValue(self.limits[limit]['state'])

    def check_modules(self, modules_manager):
        for act in self.actuators_name:
            if act not in modules_manager.actuators_name:
                logger.warning(f'The actuator {act} defined in the PID model is not present in the Dashboard')
                return False
        for det in self.detectors_name:
            if det not in modules_manager.detectors_name:
                logger.warning(f'The detector {det} defined in the PID model is not present in the Dashboard')

    def update_detector_names(self):
        names = self.pid_controller.settings.child('main_settings', 'detector_modules').value()['selected']
        self.data_names = []
        for name in names:
            name = name.split('//')
            self.data_names.append(name)

    def update_settings(self, param):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        To be overwritten in child class
        """
        if param.name() == '':
            pass

    def ini_model(self):
        self.apply_limits()
        self.setpoint(self.setpoint_ini)
        self.apply_constants()

    def convert_input(self, measurements: DataToExport) -> DataToExport:
        """
        Convert the measurements in the units to be fed to the PID (same dimensionality as the setpoint)
        Parameters
        ----------
        measurements: DataToExport
         DataToExport object from which the model extract a value of the same units as the setpoint

        Returns
        -------
        DataToExport: the converted input as 0D DataCalculated stored in a DataToExport
        """
        raise NotImplementedError

    def convert_output(self, outputs: List[float], dt, stab=True) -> DataToActuatorPID:
        """
        Convert the output of the PID in units to be fed into the actuator
        Parameters
        ----------
        outputs: (list of float) output value from the PID from which the model extract a value of the same units as the actuator
        dt: (float) elapsed time in seconds since last call
        Returns
        -------
        DataToActuatorPID: the converted output as a DataToActuatorPID object (derived from DataToExport)

        """
        self.curr_output = outputs
        return DataToActuatorPID('pid', mode='rel',
                                 data=[DataActuator(self.actuators_name[ind], data=outputs[ind])
                                       for ind in range(len(outputs))])


def main(xmlfile):
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils.config import get_set_preset_path
    from pathlib import Path
    from qtpy import QtWidgets

    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dashboard = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(xmlfile)
    if file.exists():
        dashboard.set_preset_mode(file)
        # prog.load_scan_module()
        pid_area = DockArea()
        pid_window = QtWidgets.QMainWindow()
        pid_window.setCentralWidget(pid_area)

        prog = dashboard.load_pid_module(pid_window)

    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_PID Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    sys.exit(app.exec_())


def get_models(model_name=None):
    """
    Get PID Models as a list to instantiate Control Actuators per degree of liberty in the model

    Returns
    -------
    list: list of disct containting the name and python module of the found models
    """
    from pymodaq.extensions.pid.utils import PIDModelGeneric
    models_import = []
    discovered_models = get_entrypoints(group='pymodaq.pid_models')
    if len(discovered_models) > 0:
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        model_module = importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        classes = inspect.getmembers(model_module, inspect.isclass)
                        for name, klass in classes:
                            if klass.__base__ is PIDModelGeneric:
                                models_import.append({'name': mod.name, 'module': model_module, 'class': klass})
                                break

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)
