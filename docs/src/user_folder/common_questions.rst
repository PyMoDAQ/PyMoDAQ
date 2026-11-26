.. _common_questions:

Common questions
================

This page answers, with the shortest working path, questions people ask when they look for a Python tool to control
instruments and acquire data. Each answer points to the page with the details.

How do I control a camera and a motorized stage with a graphical interface in Python?
-------------------------------------------------------------------------------------

With PyMoDAQ, in four steps and no GUI code:

#. **Install PyMoDAQ and the plugins of your instruments.** In a Python environment (3.10 to 3.13):

   .. code-block:: bash

      pip install pymodaq pyside6      # or pyqt6
      pip install pymodaq_plugins_thorlabs   # example: plugins for your camera and your stage

   Plugins are Python packages named ``pymodaq_plugins_<name>``, they can also be installed from the plugin manager
   (see :doc:`/user_folder/plugin_manager`). The `list of supported instruments
   <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_ is large, and the ``mock`` plugins
   installed with PyMoDAQ let you try everything without hardware.

#. **Start the Dashboard.** Run ``dashboard`` (or ``pymodaq`` for the launcher) in a terminal. Add an *actuator* (the
   stage, a *DAQ_Move* module) and a *detector* (the camera, a *DAQ_Viewer* module) and pick the plugin of each
   instrument (:doc:`/user_folder/dashboard_control_modules`). Initialize them: the camera has its live viewer,
   the stage its position control, and all the parameters of the instruments are in the settings trees.

#. **Save the setup.** The Dashboard saves the whole configuration as an *experiment* file, loaded at next start.

#. **Acquire and scan.** Snap or grab images from the camera viewer, move the stage from its module, or
   open the *DAQ Scan* extension to move the stage in steps and record an image at each position, saved in an HDF5 file
   with the axes and units (:doc:`/extensions_folder/daq_scan/daq_scan`).

If you want the same from a script instead of the GUI, see the next question.

How do I drive the same instruments from a Python script or a Jupyter notebook?
-------------------------------------------------------------------------------

Start the Dashboard (or load your experiment with it) and use the scripting API, which connects to the running modules
over LECO:

.. code-block:: python

   from pymodaq.scripting import Actuator, Detector
   from pymodaq_data import Q_

   stage = Actuator('Stage')      # names of the modules in the Dashboard
   camera = Detector('Camera')

   stage.move_abs(Q_('10 mm')).result()
   data = camera.snap().result()  # a DataToExport, with axes and units

Details in :doc:`/user_folder/scripting`. The data objects are described in :doc:`/data_management/data_objects`.

How do I scan a parameter and save the data in a file?
------------------------------------------------------

Use the DAQ Scan extension of the Dashboard: choose the actuators to scan, the detectors to record and the scan
type (linear, random, spiral, adaptive...), then start. Data are saved in HDF5 with their axes
(:doc:`/extensions_folder/daq_scan/daq_scan`, :doc:`/data_management/saving_loading_data`). The
*DAQ Logger* extension records detectors over time (:doc:`/extensions_folder/daq_logger`).

Is my instrument supported by PyMoDAQ?
--------------------------------------

Search for it in the :ref:`Plugin Manager<plugin_manager>` (Dashboard, *Tools* menu, or the ``plugin_manager`` command):
the search box looks in the name of the plugins and in the instruments they list, and the table shows the instruments of
each plugin. The same list, compiled every week from the README of the plugins published on PyPI, is on the
`plugin list <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_ and, for programs, in
`instruments.json <https://raw.githubusercontent.com/PyMoDAQ/pymodaq_plugin_manager/main/doc/instruments.json>`_ (plugin,
versions of PyMoDAQ it works with, instruments by type). If your model is not listed, a plugin for another model of the
same manufacturer may already exist and be easy to extend: see the next question.

How do I add support for an instrument that has no plugin yet?
--------------------------------------------------------------

Write a plugin: start from the `plugin template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_ and follow
:doc:`/tutorials/first_plugin` (a complete actuator and detector in under 80 lines each, with a test that runs
without hardware). The plugin only wraps the instrument library; the GUI, scans and saving come for free.

How do I use the instruments of my lab from a remote computer?
--------------------------------------------------------------

PyMoDAQ modules can be exposed over the network with LECO (:doc:`/user_folder/leco`) and driven by scripts or other
PyMoDAQ instances.

How does PyMoDAQ compare with PyVISA, QCoDeS or Bluesky?
--------------------------------------------------------

See :doc:`/user_folder/alternatives`.

Which operating systems and Python versions are supported?
----------------------------------------------------------

Windows and Linux, Python 3.10 to 3.13, with PyQt6 or PySide6 (:doc:`/quick_start`). Whether a given instrument works
depends on its plugin (some vendor libraries exist on Windows only).

Is PyMoDAQ free, and who maintains it?
--------------------------------------

PyMoDAQ is free and open-source (MIT license) and is supported by the French CNRS. Its source is on
`GitHub <https://github.com/PyMoDAQ/PyMoDAQ>`_, it is published on PyPI and it is cited in
:doc:`/about`.
