.. _release_2:

=========================
PyMoDAQ 2 (2.0.0-2.2.6)
=========================

PyMoDAQ 2.0.0 was released on 2020-06-21 and the series ended with 2.2.6 on 2020-11-17.

2.2 (October-November 2020): plugins and configuration
======================================================

* **Plugin Manager** to fetch, update or remove plugins, replacing the multiple plugin repositories that made
  installation tiresome (2.2.1)
* Configuration file editable from a GUI, opened from the Dashboard menu (2.2.1)
* Plugins discoverable through **entry points**, with a separate repository for the base plugins (2.2.0)
* Local configuration file (TOML) to pre-fill defaults: author name, preset file, log level, network IP/port...
  (2.2.0)

2.1 (October 2020): remote control and custom applications
==========================================================

* **Remote manager** to control DAQ_Moves and DAQ_Viewers from the Dashboard with keyboard shortcuts or a gamepad
  (2.1.0)
* Documentation and code example to write custom applications using PyMoDAQ modules (2.1.0)

2.0 (June 2020): scans and extensions
=====================================

* **Dashboard** and **DAQ_Scan** separated into two objects and interfaces: the Dashboard becomes the main entry
  point and allows extensions to be written
* **DAQ_Logger** extension to log data from several DAQ_Viewers to SQL databases or h5 files
* Scans: **adaptive** scans (with a module manager to select active actuators and detectors), **tabular** scans (list
  of discrete points), **sequential** scans (no actuator limit), specific live and H5Browser plotting for
  tabular/adaptive scans, and the possibility to load an existing h5 dataset to continue a scan after a crash
* Viewer2D can plot a series of points not on a grid (triangulation); the NDViewers display correct axes
* ROI manager in the Dashboard to configure the ROIs of all detectors; ROI saving as xml patched
* hdf5 saving and browsing as a module wrapping several backends (pytables, h5py, h5pyd): ``H5Saver``,
  ``H5Backends`` and ``H5Browser``
* Plugins can save temporary data into h5 files (high-throughput acquisition) and can emit a signal to modify the UI
  general settings of DAQ_Move or DAQ_Viewer
* Rotating log file with sub-names from the script where the entry comes from
* A Chrono/Timer UI (``chrono_timer``) and a cleaned, documented TCP/IP communication for DAQ_Move and DAQ_Viewer
* Programmatic entries in scalable group parameters through the ``values`` key
