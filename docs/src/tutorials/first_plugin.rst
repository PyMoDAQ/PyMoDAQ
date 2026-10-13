.. _first_plugin:

Your first plugin in 10 minutes
===============================

This page is the shortest path to a working instrument plugin: one actuator and one detector for a made-up
instrument, **Acme**, each under 80 lines, and a test that runs them without hardware. Replace *Acme* by the name of your
instrument (``Acme`` becomes ``Xxxx`` in the file and class names, see the :ref:`naming convention
<instrument_plugin_doc>`). The complete reference is the :ref:`plugin tutorial <plugin_development>`.

The code of this page is tested: the files below are written to a package and checked by PyMoDAQ's test suite.

Start from the template
-----------------------

Create your repository from the `plugin template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_ (see
:ref:`new_plugin`), rename the package to ``pymodaq_plugins_acme`` (the name must start with ``pymodaq_plugins_``), then
install it from the folder of the repository::

    pip install -e .

Delete the template files you do not need. The package then contains, in
``src/pymodaq_plugins_acme/``, the folders ``hardware``, ``daq_move_plugins`` and ``daq_viewer_plugins/plugins_1D``
(the paths below are relative to ``src/``).

1. Keep the instrument behind a small wrapper
---------------------------------------------

Communication with the instrument belongs to a wrapper class of the ``hardware`` folder, or to the Python library of the
manufacturer. The plugin only translates between PyMoDAQ and this wrapper. Here is a made-up one, so that everything
runs without hardware:

.. code-block:: python
   :caption: pymodaq_plugins_acme/hardware/acme_wrapper.py

   """Stands for the Python wrapper of the vendor library (here: made up, it needs no hardware)."""
   import numpy as np


   class AcmeController:
       def __init__(self, port: str = 'COM1'):
           self.port = port
           self.position = 0.  # mm

       def move_to(self, mm: float):
           self.position = mm

       def read_position(self) -> float:
           return self.position

       def read_spectrum(self, npts: int) -> np.ndarray:
           return np.random.random(npts)

       def close(self):
           pass

2. The actuator
---------------

File ``daq_move_Acme.py`` holds the class ``DAQ_Move_Acme``. Positions go in and out as ``DataActuator`` objects
with **units**. The five methods ``ini_stage``, ``get_actuator_value``, ``move_abs``, ``move_rel`` and ``close`` are
required (see :ref:`plugin_contract`).

.. code-block:: python
   :caption: pymodaq_plugins_acme/daq_move_plugins/daq_move_Acme.py

   from pymodaq.control_modules.move_utility_classes import (
       DAQ_Move_base, comon_parameters_fun, main, DataActuatorType, DataActuator)

   from pymodaq_plugins_acme.hardware.acme_wrapper import AcmeController


   class DAQ_Move_Acme(DAQ_Move_base):
       """Acme linear stage, one axis.

       Tested with the Acme stage model S1 on COM3 (PyMoDAQ 5.3, Windows 11).
       Needs the Acme driver from the manufacturer's website.
       """
       is_multiaxes = False
       _axis_names = ['linear']
       _controller_units = 'mm'
       _epsilons = [0.01]  # the stage is at its target if closer than that
       data_actuator_type = DataActuatorType.DataActuator  # always keep this line

       params = [
           {'title': 'Port:', 'name': 'port', 'type': 'str', 'value': 'COM3'},
       ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names,
                                epsilon=_epsilons)

       def ini_attributes(self):
           self.controller: AcmeController = None

       def ini_stage(self, controller=None):
           if self.is_master:
               self.controller = AcmeController(self.settings['port'])
           else:  # a slave axis is given the controller of the master
               self.controller = controller
           return 'Acme stage ready', True  # (info, initialized)

       def close(self):
           if self.is_master and self.controller is not None:
               self.controller.close()

       def get_actuator_value(self) -> DataActuator:
           pos = DataActuator(data=self.controller.read_position(),
                              units=self.axis_unit)
           return self.get_position_with_scaling(pos)

       def move_abs(self, value: DataActuator):
           value = self.check_bound(value)  # stay within the bounds
           self.target_value = value
           value = self.set_position_with_scaling(value)
           self.controller.move_to(value.value(self.axis_unit))

       def move_rel(self, value: DataActuator):
           self.move_abs(self.current_value + value)

       def move_home(self):
           self.move_abs(DataActuator(data=0., units=self.axis_unit))

       def stop_motion(self):
           pass  # call the stop command of the controller here if it has one


   if __name__ == '__main__':
       main(__file__)

3. The detector
---------------

File ``daq_1Dviewer_Acme.py`` holds the class ``DAQ_1DViewer_Acme``. Data leave the plugin as a ``DataToExport``
emitted with ``self.dte_signal``, with units and axes. The required methods are ``ini_detector``, ``grab_data``,
``stop`` and ``close``.

.. code-block:: python
   :caption: pymodaq_plugins_acme/daq_viewer_plugins/plugins_1D/daq_1Dviewer_Acme.py

   import numpy as np

   from pymodaq.control_modules.viewer_utility_classes import (
       DAQ_Viewer_base, comon_parameters, main)
   from pymodaq.utils.data import DataFromPlugins
   from pymodaq_data.data import DataToExport, Axis

   from pymodaq_plugins_acme.hardware.acme_wrapper import AcmeController


   class DAQ_1DViewer_Acme(DAQ_Viewer_base):
       """Acme spectrometer, one trace of `npts` points.

       Tested with the Acme spectrometer SP-1 (PyMoDAQ 5.3, Windows 11).
       """
       params = comon_parameters + [
           {'title': 'Port:', 'name': 'port', 'type': 'str', 'value': 'COM4'},
           {'title': 'Points:', 'name': 'npts', 'type': 'int', 'value': 100,
            'min': 1},
       ]

       def ini_attributes(self):
           self.controller: AcmeController = None

       def ini_detector(self, controller=None):
           if self.is_master:
               self.controller = AcmeController(self.settings['port'])
           else:
               self.controller = controller
           return 'Acme spectrometer ready', True  # (info, initialized)

       def close(self):
           if self.is_master and self.controller is not None:
               self.controller.close()

       def grab_data(self, Naverage=1, **kwargs):
           npts = self.settings['npts']
           signal = self.controller.read_spectrum(npts)
           wavelength = Axis('wavelength', units='nm',
                             data=np.linspace(400, 800, npts), index=0)
           self.dte_signal.emit(DataToExport('acme', data=[
               DataFromPlugins('spectrum', data=[signal], dim='Data1D',
                               labels=['intensity'], units='V', axes=[wavelength])
           ]))

       def stop(self):
           pass  # call the stop command of the controller if it has one

       def commit_settings(self, param):
           pass  # send the changed setting to the hardware


   if __name__ == '__main__':
       main(__file__)

4. Test it without hardware
---------------------------

Replace the wrapper by a fake one that has the same methods and runs the plugin class with the helpers of
``pymodaq.utils.plugin_testing``. ``monkeypatch.setattr`` replaces the name ``AcmeController``, as the plugin module
imports it, by the fake (see :ref:`plugin_behaviour_tests`). Put this file in the ``tests`` folder:

.. code-block:: python
   :caption: tests/test_acme.py

   import numpy as np
   import pytest

   from pymodaq.utils.plugin_testing import (make_actuator, move_abs_and_wait, move_rel_and_wait,
                                             make_detector, grab_and_wait, assert_units)
   from pymodaq_plugins_acme.daq_move_plugins import daq_move_Acme
   from pymodaq_plugins_acme.daq_viewer_plugins.plugins_1D import daq_1Dviewer_Acme


   class FakeController:
       def __init__(self, port):
           self.position = 0.
       def move_to(self, mm): self.position = mm
       def read_position(self): return self.position
       def read_spectrum(self, npts): return np.ones(npts)
       def close(self): pass


   def test_move_abs(qapp, monkeypatch):
       monkeypatch.setattr(daq_move_Acme, 'AcmeController', FakeController)
       actuator = make_actuator(daq_move_Acme.DAQ_Move_Acme)
       assert actuator.initialized
       position = move_abs_and_wait(actuator, 2.5)
       assert position.value('mm') == pytest.approx(2.5, abs=0.01)
       position = move_rel_and_wait(actuator, 0.5)
       assert position.value('mm') == pytest.approx(3.0, abs=0.01)
       actuator.close()


   def test_grab(qapp, monkeypatch):
       monkeypatch.setattr(daq_1Dviewer_Acme, 'AcmeController', FakeController)
       detector = make_detector(daq_1Dviewer_Acme.DAQ_1DViewer_Acme)
       dte = grab_and_wait(detector)
       assert_units(dte)
       assert dte[0].data[0].shape == (100,)
       detector.close()

5. Check and run
----------------

From the folder of the repository::

    check_plugin    # static report: names, entry points, required methods, units...
    pytest          # the template tests and yours

Both have to pass before a contribution (see :ref:`check_plugin_command`). Then adapt the wrapper and the parameters to
your instrument, and say in your contribution what was tested on the real instrument and what only against a fake.
