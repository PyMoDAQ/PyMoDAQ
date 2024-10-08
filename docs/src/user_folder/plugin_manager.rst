
.. _plugin_manager:


Plugin Manager
--------------

Any new hardware has to be included in PyMoDAQ within a :term:`plugin`. A PyMoDAQ's plugin is a python package
containing several added functionalities such as instruments objects. A instrument object is a class inheriting from
either
a ``DAQ_Move_base`` or a ``DAQ_Viewer_base`` class and implements mandatory methods for easy and quick inclusion
of the instrument within the PyMoDAQ control modules.

The complete list of available Instrument Plugins is maintained on this GitHub `repository`__.

While you can install them manually (for instance using ``pip install plugin_name``), from PyMoDAQ 2.2.2 a plugin
manager is available. You can open it from the **Dashboard** in the help section or directly using the command
line: ``python -m pymodaq_plugin_manager.manager`` or directly ``plugin_manager``

This will open the Plugin Manager User Interface as shown on figure :numref:`fig_plug_manager` listing the available
plugins packages that can be either *installed*, *updated* or *removed*. It includes a description of the content of
each package and the instruments it interfaces. For instance, on figure :numref:`fig_plug_manager`, the selected *Andor*
plugin package is selected and includes two plugins: a Viewer1D to interface Andor Shamrock spectrometers and a Viewer2D
to interface Andor CCD camera.

   .. _fig_plug_manager:

.. figure:: /image/installation/plugin_manager.png
   :alt: plugin_manager

   Plugin Manager interface


__ https://github.com/PyMoDAQ/pymodaq_plugin_manager

