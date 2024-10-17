  .. _glossary:

Glossary Terms
==============

Here are some definitions of the specific terms used in the PyMoDAQ documentation:

.. glossary::

  Actuator
    Any instrument with a controllable varying parameter

  CLI
    Command Line Interface: program to be used within a shell/command prompt

  conda
    *conda* is an environment manager part of the
    `Miniconda <https://docs.anaconda.com/miniconda/>`_ distribution (or Anaconda).

    .. note::
      *conda* as a :term:`CLI` is part of Anaconda or Miniconda that have restrictions in terms of licencing.
      *conda* should therefore not be used anymore. Please use :term:`mamba` as a replacement.

  Control Modules
    GUI for actuators and detectors, with subsequent classes: ``DAQ_Move`` and ``DAQ_Viewer``, see :ref:`control_modules`

  DashBoard
    GUI allowing configuration and loading of a :term:`preset` file of actuators and detectors. You can also start
    extensions from its GUI such as the :ref:`DAQ_Scan_module`, :ref:`DAQ_Logger_module`, ... See
    :ref:`the Dashboard section <Dashboard_module>` of the documentation.

  DataDim
    Enum for the dimensionality representation of the data object, for instance scalars have a dimensionality *Data0D*,
    waveforms or vectors have *Data1D* dimensionality, camera's data are *Data2D*, and hyperspectral (or other) are
    *DataND*

  DataDistribution
    Enum for the distribution type of the data object. Data can be stored on linear grid (think about an oscilloscope
    trace having a fixed time interval, or camera having a regular grid of pixels) or stored on non uniform and non
    linear "positions", for instance data taken at random time intervals. Data can therefore have two distributions:
    **uniform** or **spread**.

  DataSource
    Enum informing about the source of the data object, for instance raw from a  detector or processed from
    mathematical functions (from ROI, ...)

  Detector
    Any instrument generating data to be recorded

  dte
    Short name for ``DataToExport`` object

  dwa
    Short name for ``DataWithAxes`` object

  environment
    A Python virtual **environment** consists of two essential components: the Python interpreter that the virtual
    environment runs on and a folder containing third-party libraries installed in the virtual environment.
    These virtual environments are isolated from the other virtual environments, which means any changes on
    dependencies installed in a virtual environment don’t affect the dependencies of the other virtual environments
    or the system-wide libraries. Thus, we can create multiple virtual environments with different Python versions,
    plus different libraries or the same libraries in different versions.

  mamba
    *mamba* is a command line tool part of the
    `Miniforge <https://github.com/conda-forge/miniforge/>`_ distribution, that is recommended as part of
    :ref:`PyMoDAQ installation <quick_start>`. In the PyMoDAQ project, *mamba* is exclusively used as a *Python
    environment manager*.
    It is not used as a *package manager*, so the command
    *mamba install ...* will not be used. We will rather use :term:`pip <pip & PyPI>` as a *package manager*.

  Module
     A module in the python sense is an importable object either a directory containing an *__init__.py* file or a
     python file containing data, functions or classes.

.. note::
    If there is code that can be executed within your module but you don't want it to be executed when importing,
    make sure to protect the execution using a : ``if __name__ == '__main__':`` clause.

.. glossary::

  Navigation
    See :term:`signal`.

  pip & PyPI
    *pip* is the official Python package manager and the one that is used for the PyMoDAQ project. *pip* downloads
    Python packages that are stored in the `PyPI <https://pypi.org/>`_ (Python Package Index) servers.

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
    * **Extensions** located in a `extensions` folder: scripts and classes allowing to build extensions on top of
      the :ref:`Dashboard_module`

    Entry points python mechanism is used to let know PyMoDAQ of installed Instrument, PID models or extensions plugins.

.. glossary::

  Plugin Manager
    The :ref:`Plugin Manager <section_installation>` is a module of PyMoDAQ that ease the installation
    of plugins. It implements a simple graphical interface for the user to easily manage the plugins that are installed
    in his environment. The Plugin Manager uses a parser on the PyPI forge to propose any Python packages whose
    name starts by *pymodaq_plugins_...*.

  Preset
    XML file containing the number and type of control modules to be used for a given experiment. You can
    create, modify and load a preset from the :term:`Dashboard` menu bar.

  Signal
    Signal and Navigation are terms taken from the hyperspy package vocabulary. They are useful when dealing with
    multidimensional data.
    Imagine data you obtained from a camera (256x1024 pixels) during a linear 1D scan of one actuator (100 steps).
    The final shape of the data would be (100, 256, 1024). The first dimension corresponds to a Navigation axis
    (the scan), and the rest to Signal axes (the real detector's data).
    The corresponding data has a dimensionality of DataND and a representation of (100|256,1024).
