.. _release_1:

==========================
PyMoDAQ 1 (1.0.0-1.6.4)
==========================

PyMoDAQ 1.0.0 was released on 2018-12-10 and the series ended with 1.6.4 on 2019-11-12.

1.6 (September-November 2019): TCP/IP and cleaning
==================================================

* **TCP/IP** communication for the Move and Viewer modules, with a TCP server plugin to link any module on a distant
  computer (1.6.0); detector axes sent back to the TCP server for correct plotting (1.6.1)
* Exact location of exceptions in the logging, removal of unnecessary dependencies (``Dask``, over-specific plugin
  requirements such as ``win32com``), switch of the license to CECILL-B and lowercase names in the GitHub repository
  (1.6.2-1.6.4)

1.5 (July 2019): data saving, PID and ROI
=========================================

* ``H5Saver`` object simplifying data saving and adding mandatory metadata; axes labels and units saved as metadata
  and displayed in the H5Browser
* Exported viewer data contain axis information (values, label, units, type of data)
* **PID** controller using PyMoDAQ modules and custom PID models, usable as an actuator within DAQ_Scan and running
  in its own thread; DAQ_Scan acquisition loop in a parallel thread
* Viewer1D and Viewer2D share the same ``ROIManager``; DAQ_Scan does not save ROI-generated data by default
* Navigator double-click sends the clicked position to the connected slots; legend of Viewer1D fixed

1.4 (February-April 2019): scanner module
=========================================

* **Scanner** module dealing with line or area selections within Viewer2D modules, used by DAQ_Scan
* H5Browser context menu to export data as text
* ``acq_time_s`` field in the exported data of each viewer; debug info with package, method and script line
* macOS fix for ``ctypes`` imports in ``daq_utils`` (1.4.2)

1.3 (February 2019): navigator
==============================

* DAQ_Scan **navigator**: a 2D area showing all the 2D scans of the current h5 file at their position
* ``_controller_units`` parameter of the DAQ_Move plugins; fixed the final saving step of DAQ_Scan

1.2 (January 2019): area scans
==============================

* DAQ_Scan scans defined by selecting an area in a Viewer2D (rectangle for 2D scans, polylines for 1D scans)
* Option to save all data in independent files
* Overshoot configuration: DAQ_Move actions triggered by detected values

1.1 (December 2018): averaging and plugins
==========================================

* DAQ_Scan averaging, with a dedicated dock showing the current average (1.1.2)
* Plugins removed from the main tree and installable from GitHub or PyPI as external libraries; ``preset_mode``
  folder moved relative to the user home (1.1.0)
* Fixed background subtraction in DAQ_Viewer (1.1.2)

1.0 (December 2018)
===================

* All modules renamed in lowercase, ``viewer_multicolor`` renamed ``viewer2D`` (1.0.0)
* Entry points tested after installation (1.0.1)
