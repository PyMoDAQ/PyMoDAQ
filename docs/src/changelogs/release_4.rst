.. _release_4:

==========================
PyMoDAQ 4 (4.0.1-4.4.11)
==========================

Summary of the PyMoDAQ 4 series, from 4.0.1 (2023-04-25) to 4.4.11 (2025-04-03). Pull requests (#NNN) refer to the
`PyMoDAQ repository <https://github.com/PyMoDAQ/PyMoDAQ>`_.

.. contents::
   :local:
   :depth: 2

Highlights
==========

PyMoDAQ 4 introduced the **data management** framework (``DataWithAxes``, ``DataToExport``, ``DataActuator``),
**extensions** discovered through entry points, the **LECO** communication protocol, and in its last minor releases
a consistent handling of **units** for actuators and data.

4.0 (April-November 2023): data management and plugin discovery
===============================================================

* **Data management** objects used throughout the modules; the ``daq_utils`` package was renamed: #86, #99, #85
* DAQ_Viewer fully uses ``DataToExport`` and emits dedicated signals: #124, #127; actuator positions use
  ``DataActuator``: #147
* Exporters of data and h5 nodes, grouping and filtering of live data by source when saving: #77, #100, #103
* **Console extension**: #84; **DAQ Logger** for PyMoDAQ 4: #113; **Navigator** connected to the scan: #107, #110
* DAQ_Scan: averaging, batch scans, live plots, 0D data grouping: #104, #105, #115, #117
* **Entry points** to discover plugins and extensions, extensions management: #130, #131, #133, #143
* PID refactoring: #148; list parameters as dict and display of plugin configuration: #145
* Documentation: PID module, plugin development tutorials, contributing to the documentation: #92, #120, #125

4.1 (January-May 2024): settings, scans and data chunks
=======================================================

* **TCP/IP communication for PyMoDAQ 4** with serialization/deserialization: #183, #184
* **Custom scanners**, 1D sparse scan, saving of scanner settings: #198, #203, #220
* **Enlargeable data chunks** for saving and loading: #216, #218
* Settings: edition during grab, config modification, combo entries with a dict, checkbox for list items: #221,
  #189, #213
* Viewers: aspect ratio in Viewer2D, overlay in the 1D viewer, ROI improvements, ``plot`` extra attributes: #225,
  #186, #226, #223
* DB logger for PyMoDAQ 4: #219; h5 node exporters: #197
* Documentation: Linux installation, Git tutorial, axis handling in actuators: #182, #233, #171

4.2 (May-August 2024): LECO and optimization
============================================

* **LECO protocol** introduced, with ``LECODirector`` for DAQ_Move/DAQ_Viewer, coordinator start and PyLECO
  integration: #267, #269, #300, #275
* **Bayesian optimizer** extension: #295
* Interactive data plotting and ROI in viewers, enlargeable saving/loading, scatter plots: #266, #271, #278, #292
* Automatic save/load of settings values (bounds, utility function): #296
* Plugin listing: #302; documentation for data plotting and analysis notebooks: #281, #282

4.3 (August-September 2024): units and architecture
====================================================

* **Data units**; ``ThreadCommand`` with ``status_sig`` everywhere; parameters serialization for TCP/IP: #356, #358,
  #360, #326
* Properties to know whether a controller is master or slave, better master/slave handling: #330, #386
* ``QApplication`` as a context manager, Dashboard loader for extensions, DAQ_Move sizing: #335, #336, #342
* Units of ``DataActuator`` emitted by plugins, controller units back compatibility: #380, #387
* Default config path for macOS: #372; citation file: #363

4.4 (September 2024-April 2025): consistent units
=================================================

* Display and controller units handled separately, units included in the serialization: #381, #385
* Dedicated user condition to check that the target has been reached: #384
* Units display fixes (``base_units``, volt, degrees): #425, #427, #452; opposite button: #448
* LECO: binary transport, qt-less standalone module example, improved serializer: #404, #413, #430
* ``bayesian-optimization`` restricted to < 2.0.0 until the new version is supported (4.4.5): #409
* Plugin entry points browsed in all discovered plugins: #442; last fixes on scan averaging and unit
  conversion of float-defined actuators: #566, #583
