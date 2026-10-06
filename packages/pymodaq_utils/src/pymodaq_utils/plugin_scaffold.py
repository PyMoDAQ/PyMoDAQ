"""Helper to add a new, correctly named, instrument to a PyMoDAQ plugin package (``pymodaq_plugins_*``).

It is a development helper, independent of the plugin checks (see :mod:`pymodaq_utils.plugin_checks`). The generated
module follows the naming convention, derives from the right base class, declares the mandatory attributes and
methods, and holds ``TODO`` comments (and ``NotImplementedError``) where the instrument specific code goes::

    python -m pymodaq_utils.plugin_scaffold move Xxxx      # actuator: daq_move_Xxxx.py, class DAQ_Move_Xxxx
    python -m pymodaq_utils.plugin_scaffold 1D Xxxx        # 1D detector: daq_1Dviewer_Xxxx.py, class DAQ_1DViewer_Xxxx

from the root of the plugin repository (or use ``--folder`` to give the package folder). The same is available from
python with :func:`create_instrument`.

.. versionadded:: 5.4.0
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from string import Template
from typing import Optional

KINDS = ('move', '0D', '1D', '2D', 'ND')

PLUGINS_INIT = '''import importlib
from pathlib import Path
from pymodaq_utils.logger import set_logger

logger = set_logger('$logger_name', add_to_console=False)

# import all the plugin modules of this folder. A module that cannot be imported (missing driver...) is logged and
# skipped. Note: PyMoDAQ uses the 'path' variable below to find the plugin modules.
for path in Path(__file__).parent.iterdir():
    try:
        if '__init__' not in str(path):
            importlib.import_module('.' + path.stem, __package__)
    except Exception as e:
        logger.warning(f"{path.stem} plugin couldn't be loaded due to some missing packages or errors: {e}")
'''

MOVE = '''"""
$class_name
"""
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, main,
                                                          DataActuatorType, DataActuator)
from pymodaq_utils.utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq_gui.parameter import Parameter

# TODO: import the python wrapper of your instrument, here we suppose it is in the hardware folder of the package
#  (it could also come from an external library like pylablib or pymeasure)
# from $package.hardware.my_wrapper import MyInstrumentWrapper


class $class_name(DAQ_Move_base):
    """Instrument plugin class for an actuator.

    TODO complete this docstring with:
      * the instrument (and models) this plugin was tested with
      * the drivers or libraries to install and where to find them
      * the specific attributes and parameters (see ``params``)
    """
    is_multiaxes = False  # TODO set to True if the controller drives several axes
    _axis_names = ['Axis1']  # TODO list (or dict name -> index) of the axes of the controller
    _controller_units = 'mm'  # TODO a unit known from pint, or a list/dict with one unit per axis
    _epsilons = 0.1  # TODO precision at which the target is considered as reached (in _controller_units)
    data_actuator_type = DataActuatorType.DataActuator
    params = [
        # TODO add here, as dicts, the settings of your instrument
    ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names)

    def ini_attributes(self):
        # TODO declare the type of the wrapper (and uncomment) for easy autocompletion
        # self.controller: MyInstrumentWrapper = None
        self.controller = None

    def get_actuator_value(self):
        """Get the current actuator value

        Returns
        -------
        DataActuator
        """
        raise NotImplementedError  # TODO remove this line and read the position from the controller below
        pos = DataActuator(data=self.controller.get_position(), units=self.axis_unit)
        pos = self.get_position_with_scaling(pos)
        return pos

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within settings) whose value has been changed by the user
        """
        # TODO apply the changes on the controller, for instance:
        # if param.name() == 'a_parameter_you_added_in_params':
        #     self.controller.apply_it(param.value())
        pass

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: object
            The controller of the master actuator in the slave case (None in the master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        raise NotImplementedError  # TODO remove this line and fill the initialization below
        if self.is_master:
            self.controller = None  # TODO instantiate the wrapper of your instrument
            initialized = True  # TODO check that the communication works
        else:
            self.controller = controller
            initialized = True

        info = 'Whatever info you want to log'
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        raise NotImplementedError  # TODO remove this line and close the communication with the controller

    def move_abs(self, value: DataActuator):
        """Move the actuator to the absolute target defined by value"""
        value = self.check_bound(value)  # if the user checked the bounds, they are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply the scaling if the user specified one
        raise NotImplementedError  # TODO remove this line and move the actuator below
        self.controller.move_abs(value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def move_rel(self, value: DataActuator):
        """Move the actuator to the relative target defined by value"""
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        value = self.set_position_relative_with_scaling(value)
        raise NotImplementedError  # TODO remove this line and move the actuator below
        self.controller.move_rel(value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def move_home(self):
        """Call the reference method of the controller"""
        raise NotImplementedError  # TODO remove this line and call the homing of the controller below
        self.controller.home()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def stop_motion(self):
        """Stop the actuator and emit the move_done signal"""
        raise NotImplementedError  # TODO remove this line and stop the controller below
        self.controller.stop()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


if __name__ == '__main__':
    main(__file__)
'''

VIEWER = '''"""
$class_name
"""
import numpy as np

from pymodaq_utils.utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

# TODO: import the python wrapper of your instrument, here we suppose it is in the hardware folder of the package
#  (it could also come from an external library like pylablib or pymeasure)
# from $package.hardware.my_wrapper import MyInstrumentWrapper


class $class_name(DAQ_Viewer_base):
    """Instrument plugin class for a $dim detector.

    TODO complete this docstring with:
      * the instrument (and models) this plugin was tested with
      * the drivers or libraries to install and where to find them
      * the specific attributes and parameters (see ``params``)
    """
    params = comon_parameters + [
        # TODO add here, as dicts, the settings of your instrument
    ]

    def ini_attributes(self):
        # TODO declare the type of the wrapper (and uncomment) for easy autocompletion
        # self.controller: MyInstrumentWrapper = None
        self.controller = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        # TODO apply the changes on the controller, for instance:
        # if param.name() == 'a_parameter_you_added_in_params':
        #     self.controller.apply_it(param.value())
        pass

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: object
            The controller of the master detector in the slave case (None in the master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        raise NotImplementedError  # TODO remove this line and fill the initialization below
        if self.is_master:
            self.controller = None  # TODO instantiate the wrapper of your instrument
            initialized = True  # TODO check that the communication works
        else:
            self.controller = controller
            initialized = True

        # initialize the viewer panel with the future type of data
        self.dte_signal_temp.emit(DataToExport(name='$name', data=[
            DataFromPlugins(name='$name', data=[$example_data], dim='Data$dim', labels=['label'])]))

        info = 'Whatever info you want to log'
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        raise NotImplementedError  # TODO remove this line and close the communication with the controller

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if the hardware can average, set hardware_averaging = True in the class
            and implement it here)
        kwargs: dict
            others optionals arguments
        """
        # TODO synchronous version (blocking), replace the example data by the data of your instrument. For an
        #  asynchronous one, start the grab with a callback that emits dte_signal when the data are ready
        data = $example_data
        self.dte_signal.emit(DataToExport(name='$name', data=[
            DataFromPlugins(name='$name', data=[data], dim='Data$dim', labels=['label'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        raise NotImplementedError  # TODO remove this line and stop the acquisition of the controller below
        self.controller.stop()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        return ''


if __name__ == '__main__':
    main(__file__)
'''

EXAMPLE_DATA = {'0D': 'np.array([0.])', '1D': 'np.zeros((10,))', '2D': 'np.zeros((10, 10))',
                'ND': 'np.zeros((5, 5, 5))'}


def find_package_folder(start: Optional[Path] = None) -> Path:
    """Find the plugin package folder (``pymodaq_plugins_*``) in the given folder, in its ``src`` subfolder or above"""
    start = Path(start or Path.cwd()).resolve()
    for folder in (start, *start.parents):
        for base in (folder, folder / 'src'):
            found = sorted(p for p in base.glob('pymodaq_plugins_*') if p.is_dir() and (p / '__init__.py').is_file())
            if found:
                return found[0]
    raise FileNotFoundError(f'No pymodaq_plugins_* package found in or above {start}, use the package folder option')


def create_instrument(kind: str, name: str, package_folder: Optional[Path] = None) -> Path:
    """Create the module of a new instrument in a plugin package

    Parameters
    ----------
    kind: str
        'move' for an actuator, or '0D', '1D', '2D', 'ND' for a detector
    name: str
        name of the instrument, starting with a capital letter (the module is daq_move_<name> or
        daq_<kind>viewer_<name>, the class DAQ_Move_<name> or DAQ_<kind>Viewer_<name>)
    package_folder: Path
        the folder of the plugin python package. Searched from the current folder if not given

    Returns
    -------
    Path: the created file

    Raises
    ------
    ValueError
        for an invalid kind, name or package
    FileExistsError
        if the module already exists
    """
    if kind not in KINDS:
        raise ValueError(f'kind should be one of {KINDS}')
    if not re.match(r'^[A-Z]\w*$', name):
        raise ValueError(f"The name '{name}' should start with a capital letter and contain only letters, digits "
                         f"or underscores")
    package_folder = Path(package_folder) if package_folder is not None else find_package_folder()
    package = package_folder.name
    if not re.match(r'^pymodaq_plugins_\w+$', package):
        raise ValueError(f"The package folder '{package}' should be named pymodaq_plugins_<name>")

    if kind == 'move':
        folder = package_folder / 'daq_move_plugins'
        module, class_name, logger_name = f'daq_move_{name}', f'DAQ_Move_{name}', 'move_plugins'
        code = Template(MOVE).substitute(class_name=class_name, package=package)
    else:
        folder = package_folder / 'daq_viewer_plugins' / f'plugins_{kind}'
        module, class_name = f'daq_{kind}viewer_{name}', f'DAQ_{kind}Viewer_{name}'
        logger_name = f'viewer{kind}_plugins'
        code = Template(VIEWER).substitute(class_name=class_name, package=package, name=name, dim=kind,
                                           example_data=EXAMPLE_DATA[kind])
    target = folder / f'{module}.py'
    if target.exists():
        raise FileExistsError(f'{target} already exists')

    folder.mkdir(parents=True, exist_ok=True)
    for init_folder in (folder.parent, folder) if kind != 'move' else (folder,):
        init = init_folder / '__init__.py'
        if not init.exists():
            init.write_text(Template(PLUGINS_INIT).substitute(logger_name=logger_name) if init_folder == folder else '')
    target.write_text(code)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description='Add a new instrument module to a PyMoDAQ plugin package')
    parser.add_argument('kind', choices=KINDS, help="'move' for an actuator, or the dimensionality of a detector")
    parser.add_argument('name', help='name of the instrument, starting with a capital letter')
    parser.add_argument('--folder', type=Path, default=None,
                        help='the pymodaq_plugins_* package folder (default: found from the current folder)')
    args = parser.parse_args(argv)
    try:
        target = create_instrument(args.kind, args.name, args.folder)
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        parser.error(str(e))
    print(f'Created {target}\nSearch for the TODO comments in it and complete them.')


if __name__ == '__main__':
    main()
