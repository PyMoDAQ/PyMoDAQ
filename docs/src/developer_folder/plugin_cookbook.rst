.. _plugin_cookbook:

Plugin cookbook
===============

Most of the work of a plugin is the communication with the instrument, and it depends on how the instrument is reached:
a text protocol, a serial line, VISA, a DLL, a .NET assembly... The package
`pymodaq_plugins_mockexamples <https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples>`__ holds a *cookbook*: short,
tested plugins, one for each of these ways, to copy from when writing the plugin of your instrument.

Each recipe runs **without hardware**: it talks to a simulated device (a *mock*) written for it, so you can try it in the
Dashboard, read it, and run its tests. Where a recipe has a port or an address, leave it to ``MOCK`` to use the simulated
device; give the real one to talk to your instrument.

How to use a recipe:

#. Choose the recipe in the list below and read the header of its files: it tells what to **copy**, what to **adapt**
   (the commands and the parameters of your instrument) and what to **keep** (the parts that PyMoDAQ needs and that are
   easy to get wrong: threads, master and slave, units...).
#. Put the communication with the instrument in a class of the *hardware* folder of your package, as the recipes do, and
   keep the plugin files thin (see :ref:`instrument_plugin_doc`).
#. Test your plugin as the recipes do, against a simulated device and the tools of ``pymodaq.utils.plugin_testing``
   (see :ref:`plugin_behaviour_tests`). A test on a simulated device checks your side of the contract with PyMoDAQ, not
   the device: say what was tried on the real instrument.

The files of the recipes are in ``src/pymodaq_plugins_mockexamples/`` of the repository. The README of the package has a
table of them (`cookbook of device patterns
<https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples#cookbook-of-device-patterns>`__).

The recipes
-----------

**An instrument with a text protocol (commands such as** ``*IDN?`` **): pymeasure** (recommended)
    ``daq_move_CookbookPymeasure``, ``daq_0Dviewer_CookbookPymeasure`` and ``hardware/pymeasure_source.py``. The
    instrument is described in a few declarative lines with
    `pymeasure <https://pymeasure.readthedocs.io>`__ (the commands to read and set a value, the validators, the checking
    of errors). Its tests send the exact commands of the manual to a protocol adapter, and also run on a simulated device.

**A serial line (RS-232, USB-serial)**
    ``daq_move_CookbookSerial``, ``daq_0Dviewer_CookbookSerial`` and ``hardware/serial_stage.py``. A driver written
    directly on ``pyserial``: the terminations of the commands, the timeouts treated as errors, one lock because the
    driver is shared by the actuator and the detector, the error queue of the device and a homing that blocks until it is
    over and then calls ``move_done``.

**VISA / SCPI instruments**
    ``daq_move_CookbookVisa``, ``daq_0Dviewer_CookbookVisa`` and ``hardware/visa_meter.py``. The same on a ``pyvisa``
    resource: explicit terminations and timeout, ``query`` versus ``write``.

**A DLL from the manufacturer (C library)**
    ``daq_move_CookbookDll`` (three axes), ``daq_0Dviewer_CookbookDll`` and ``hardware/dll_controller.py``. A ``ctypes``
    driver: the ``argtypes`` and ``restype`` of each function, the opaque handle, ``byref``, a structure filled by the
    library, error codes turned into exceptions and a callback that the library calls from one of its threads (it is kept
    alive, and it only emits a Qt signal). The library is replaced by an object used like the loaded ``CDLL``, so the code
    of the driver is the real one. ``hardware/native_library.py`` loads a library (names per platform, path from a setting
    or an environment variable, an error that lists what was tried) and ``hardware/system_library_demo.py`` shows the
    techniques on the C library of the system.

**A .NET assembly from the manufacturer**
    ``daq_move_CookbookDotNet`` (three axes), ``daq_0Dviewer_CookbookDotNet``, ``hardware/dotnet_controller.py`` and
    ``hardware/dotnet_runtime.py``. A `pythonnet <https://pythonnet.github.io>`__ driver: the ``out`` parameters that come
    back in a tuple, the events given a Python function, the exception type of the assembly, ``IDisposable``. The assembly
    is replaced by an object used like its namespace. ``hardware/system_dotnet_demo.py`` shows the techniques on the .NET
    libraries of the runtime. ``pythonnet`` needs a .NET runtime only when it talks to an assembly.

**A Python package from the manufacturer**
    There is no recipe: put it behind a class of the *hardware* folder, created by ``ini_stage`` or ``ini_detector``, as
    the drivers above, so that a simulated version of this class can replace it in the tests.

**A camera**
    ``daq_2Dviewer_CookbookCamera`` and ``hardware/mock_camera.py``: the recipe to copy for a real camera. The plugin is a
    ``CameraBase`` of ``pymodaq_plugins_utils`` (acquisition in a thread of its own, live and snap, averaging, the ROI
    drawn in the viewer, binning, FPS) and the driver follows the ``CameraDriverBase`` interface of the same package, with
    the method names of pylablib. ``daq_2Dviewer_BSCamera`` and ``hardware/beam_steering.py`` are the camera of the beam
    steering demonstrations, a plain plugin on purpose: what a camera driver gives its plugin, a region of interest and a
    binning applied by the camera (the image is smaller), an exposure time, and axes calibrated in µm that follow them.
    ``daq_2Dviewer_RoiStuff`` is the other way to select a region: it is drawn in the viewer, received by the plugin in
    ``roi_select`` and applied to the data after the grab.

**A spectrometer**
    ``daq_1Dviewer_CookbookSpectrometer``, ``daq_move_CookbookSpectrometer`` and ``hardware/spectrometer.py``. A
    detector whose axis (the wavelength in nm) changes because another module, here the actuator that turns the grating,
    moves it: the axis is asked to the instrument at every grab and sent with the data. The actuator is a slave of the
    detector and shares its instrument. The detector has the methods (``get_spectro_wl``, ``set_laser_wl``...) that the
    spectrometer extension calls.

What the recipes share
----------------------

* The simulated device is a plain Python class in the *hardware* folder, with the same public methods as the driver.
* An actuator and a detector of the same instrument get the same *Controller ID* in the Dashboard: the first initialized
  is the master and creates the driver, the other is the slave and receives it.
* A callback or an event raised by a thread of the driver never calls ``move_done`` or touches a widget: it emits a Qt
  signal, received in the thread of the plugin.
* Every actuator value and every axis has a unit.
