
.. _plugin_manager:


Plugin Manager
--------------

Any new hardware has to be included in PyMoDAQ within a :term:`plugin`. A PyMoDAQ's plugin is a python package
containing several added functionalities such as instruments objects. A instrument object is a class inheriting from
either
a ``DAQ_Move_base`` or a ``DAQ_Viewer_base`` class and implements mandatory methods for easy and quick inclusion
of the instrument within the PyMoDAQ control modules.

The complete list of available Instrument Plugins is maintained in the `pymodaq_plugin_manager`__ repository
(`table of plugins`__, updated every week from the README of the packages published on PyPI).

While you can install them manually (for instance using ``pip install plugin_name``), a plugin
manager is available. You can open it from the **Dashboard** (*Tools* menu) or directly using the command
line: ``python -m pymodaq_plugin_manager.manager`` or directly ``plugin_manager``. Only one Plugin Manager window is open
at a time.

This will open the Plugin Manager User Interface as shown on figure :numref:`fig_plug_manager` listing the available
plugins packages that can be either *installed*, *updated* or *removed*. It includes a description of the content of
each package and the instruments it interfaces. For instance, on figure :numref:`fig_plug_manager`, the selected *Andor*
plugin package is selected and includes two plugins: a Viewer1D to interface Andor Shamrock spectrometers and a Viewer2D
to interface Andor CCD camera.

   .. _fig_plug_manager:

.. figure:: /image/installation/plugin_manager.png
   :alt: plugin_manager

   Plugin Manager interface

Is my instrument supported?
+++++++++++++++++++++++++++

The *Instruments* column lists the instruments of each plugin (those of its README, section *Instruments*). Type in
the search box the name of a plugin or of an instrument: ``Kinesis``, ``iXon``, ``thorlabs kpz``. Every word must be
found; case, spaces, ``_`` and ``-`` do not matter. The *Search filter settings* check box shows where the search is
made (name, instruments, description).

The plugins are read from a list compiled every week (``instruments.json`` in the plugin manager repository, kept for 24
hours in your PyMoDAQ folder), which makes the manager start fast and works with a poor connection. A plugin published
since the last compilation can be seen by setting the environment variable ``PYMODAQ_PLUGIN_MANAGER_LIVE`` to ``1``: the
manager then browses PyPI, which is slower.

If you write a plugin, the instruments listed in the section *Instruments* of its README are what users will find
(see :ref:`plugin_development`).


__ https://github.com/PyMoDAQ/pymodaq_plugin_manager
__ https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/doc/PluginList.md
