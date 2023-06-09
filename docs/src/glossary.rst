  .. _glossary:

Glossary Terms
==============

Here are some definitions of the specific terms used in the PyMoDAQ documentation:

.. glossary::

  Actuator
    Any instrument with a controllable varying parameter

  Detector
    Any instrument generating data to be recorded

  Control Modules
    GUI for actuators and detectors, with subsequent classes: ``DAQ_Move`` and ``DAQ_Viewer``, see :ref:`control_modules`

  DashBoard
    GUI allowing configuration and loading of a *preset* of actuators and detectors. You can also start
    extensions from its GUI such as the :ref:`DAQ_Scan_module`, :ref:`DAQ_Logger_module`, ... See :ref:`Dashboard_module`

  Preset
    XML file containing the number and type of control modules to be used for a given experiment. You can
    create, modify and load a preset from the Dashboard

  DataSource
    Enum informing about the source of the data object, for instance raw from a  detector or processed from
    mathematical functions (from ROI, ...)

  DataDim
    Enum for the dimensionality representation of the data object, for instance scalars have a dimensionality *Data0D*,
    waveforms or vectors have *Data1D* dimensionality, camera's data are *Data2D*, and hyperspectral (or other) are
    *DataND*

  DataDistribution
    Enum for the distribution type of the data object. Data can be stored on linear grid (think about an oscilloscope
    trace having a fixed time interval, or camera having a regular grid of pixels) or stored on non uniform and non
    linear "positions", for instance data taken at random time intervals. Data can therefore have two ditributions:
    **uniform** or **spread**.

  Plugin
    A plugin is a python package whose name is of the type: *pymodaq_plugins_apluginname* containing functionalities
    to be added to PyMoDAQ

.. note::
    A plugin may contains added functionalities such as:

    * **Classes to add a given instrument**: allows a given instrument to be added programmatically
      in a :ref:`control_modules` graphical interface
    * **Instrument drivers** located in a `hardware` folder: contains scripts/classes to ease communication
      with the instrument. Could be third party packages such as Pymeasure
    * **PID models** located in a `models` folder: scripts and classes defining the behaviour of a given PID loop
      including several actuators or detectors,
      see :ref:`pid_model`
    * **Extensions** located in a `extension` folder: scripts and classes allowing to build extensions on top of
      the :ref:`Dashboard_module`

    Entry points python mechanism is used to let know PyMoDAQ of installed Instrument, PID models or extension plugins



