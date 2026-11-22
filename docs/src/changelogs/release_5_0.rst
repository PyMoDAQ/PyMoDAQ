.. _release_5_0:

==========================
PyMoDAQ 5.0 (5.0.0-5.0.18)
==========================

PyMoDAQ 5.0.0 was released on 2024-08-22 (pre-release), 5.0.1 on 2025-03-04, and the series ended with 5.0.18 on
2025-07-01. Pull requests (#NNN) refer to the `PyMoDAQ repository <https://github.com/PyMoDAQ/PyMoDAQ>`_.

.. contents::
   :local:
   :depth: 2

Highlights
==========

5.0 is a major rewrite: the code base is split into separate packages (``pymodaq_utils``, ``pymodaq_data``,
``pymodaq_gui`` and ``pymodaq``) with backward-compatibility layers for imports, data objects carry **units**,
and control modules communicate with ``ThreadCommand`` everywhere. The Dashboard becomes a ``CustomApp`` and the
control modules can be reshaped by the instrument plugins.

Major new features
==================

* **Data units** for the data objects and actuators: #356, #358; new ``angle`` method on data objects: #357;
  conversion of units for float-defined actuators: #583; degrees kept when specified: #408; bounds handling for
  out-of-range values in ``DataActuator``: #530
* ``ThreadCommand`` and ``status_sig`` used everywhere (including DAQ_Scan): #360, #349
* **Dashboard inherits CustomApp**: #429; Dashboard loader for extensions: #336
* **Control modules UI** can be modified by the plugin: #397, #399; new control modules for PID setpoints used as
  actuators: #378, #379, #389
* New ``custom_command`` in control modules, convenience methods for the abs/rel spinboxes, spinbox shortcuts: #531,
  #532, #535
* Mechanism to obtain the crosshair of a viewer in a plugin: #492
* New ``pymodaq_updater`` (check for new versions): #513, #639; ``pymodaq_modules`` update and documentation: #512
* Parameters serialization for TCP/IP: #326; serialization tests for ``DataActuator`` and ``DataToActuators``: #467
* Data and display: slider suffix and SI prefix: #328; H5Browser ``load_file``: #327; confirmation before
  overwriting an existing file: #334; ``overwrite`` parameter to write on an existing file: #545
* Backward compatibility with 4.x plugins and imports (``enums`` module, specific imports, callables from 4 to 5):
  #447, #493, #495, #516, #540
* Python 3.10 serialization support, ``mkQApp`` instead of ``QApplication`` calls, PySide6 GitHub actions: #571,
  #488, #463
* Documentation: miniforge/mamba installation, *lab stories* (Arduino on Ubuntu), documentation clean-up, plugin
  tutorials: #407, #461, #499, #503, #504, #364

Bug fixes (5.0.2-5.0.18)
========================

* **5.0.2**: LECO serializer imports and actuator, better scan averaging: #542, #544, #565
* **5.0.3-5.0.4**: no polling of the final position outside scans, epsilons defined as a dict: #569, #575
* **5.0.5**: unit conversion for float-defined actuators: #583
* **5.0.6-5.0.7**: package version restrictions, default preset update: #600, #607
* **5.0.8-5.0.10**: DAQ_Move bounds check, units in scaling/offset conversion, overshoot out of bounds: #613, #614,
  #615
* **5.0.11-5.0.12**: ``Hz`` and ``rpm`` as displayed units: #618, #624
* **5.0.13-5.0.15**: package and ``pyleco`` version ranges, update checker no longer installs packages: #637, #643,
  #639
* **5.0.16-5.0.17**: DAQ_Scan units, values expressed in the given axis units, logging with ``exc_info``: #648, #651,
  #649
* **5.0.18**: backward compatibility for ``config_saver_loader``, ``check_data_type`` in DAQ_Move: #660, #661
