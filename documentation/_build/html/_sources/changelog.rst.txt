:orphan:

=========
Changelog
=========

* :feature:`0` DAQ_Scan: possibility to load a dataset h5file in order to pursue scans within a given dataset (mostly in
  case of program crashing, so preventing the automated new dataset file creation at program load)
* :bug:`0` patch to allow the 'values' key in the def of a group Parameter so that scalable groups can have programmatic
  entries, see DAQ_0DViewer_NIDAQmx params for instance
* :release:`1.6.4 <2019-11-12>`
* :bug:`0` cleaning of various little bugs
* :release:`1.6.3 <2019-10-14>`
* :bug:`14` Logger node was not saved properly from daq_scan
* :feature:`13` Added axes labels and units within h5 browser when looking at live scan registered data
* :support:`12` Changed the case to lower in the github repo (was done in windows who doesn't care between lower or
  upper so was not applying changes on github...
* :bug:`12` Removed too specific package requirements for plugins (win32com for instance)
* :support:`7` Changed Licence specification to CECILL-B
* :bug:`6` Removed dependance of unnecessary Dask package
* :release:`1.6.2 <2019-09-16>`
* :bug:`0` pep8 related modification of variable names not taken into account in version 1.6.1 and producing errors in daq_scan module
* :release:`1.6.1 <2019-09-10>`
* :feature:`0` Added sending detector axis from tcp/ip back to tcp server for correct plotting
* :bug:`0` Error in a tcp/ip communication (wrong signature of send_string method)
* :release:`1.6.0 <2019-09-04>`
* :feature:`0` General use of PyMoDAQ Viewer and Move modules can now be done using TCP/IP. A TCP Server plugin is
  available for each, to be loaded on the main computer. Then **Any Module** on distant computer can be linked to this server
* :release:`1.5.1 <2019-07-22>`
* :bug:`3` PID models package installation added to pymodaq setup
* :release:`1.5.0 <2019-07-22>`
* :feature:`0` DAQ_Scan module's H5Saver object has now by default the option to **not** save the ROI generated data.
  Only the live plots datas are still saved by default.
* :feature:`0` Viewer 1D and 2D share now the same object ROIManager to deal with their regions of interest
* :feature:`0` The pid_module can be used as an actuator within DAQ_Scan (using the preset_manager configuration)
* :feature:`0` DAQ_Scan module has now its acquisition loop within a parallel thread
* :feature:`0` pid_controller module modified to work in a parallel thread
* :bug:`0` viewer1D displayed incorrectly the legend, now fixed
* :feature:`0` pid_controller module added in daq_utils module: enable a PID loop using pymodaq modules and custom
  written PID models (see documentation)
* :feature:`0` Viewers: exported data now contains axis information as a dict containing data (values of the axis),
  label and units and type of data (raw or generated from a ROI)
* :feature:`0` Uniformity of the saved h5 files. Axes labels and units are added as metadata and displayed in H5Browser
* :feature:`0` creation of the H5Saver object: simplifies the data saving from pymodaq modules and adds all mandatory metadata
* :bug:`0` Navigator: double click option sends the clicked position to connected slots
* :bug:`0` DAQ_Scan: when no live plot is possible (too high dimensionality) no more scan datas are saved
* :release:`1.4.2 <2019-04-22>`
* :bug:`0` issue with ctypes imports in daq_utils on macos Now ok
* :feature:`0` added a field 'acq_time_s' in the exported data from each viewer. To be used to track at what time a
  given dataset has been recorded
* :release:`1.4.1 <2019-02-16>`
* :bug:`0` cleaning up of a few bugs
* :release:`1.4.0 <2019-02-15>`
* :feature:`0` all modules: debug info contains now name of package, method and script line where the error has been generated
* :feature:`0` h5_browser: a right click on tree items shows a context menu. so far possibility to export current item (data)
  in ascii text file (%.6e precision format).
* :feature:`0` module scanner (daq_utils.scanner) has been created. Deals with lines or area selections within any viewer2D modules. Used for DAQ_Scan
  and some others plugins (for area selection if needed). Most of the scan type settings (of daq_scan) have been moved to scanner
  that is now a subobject of daq_scan
* :release:`1.3.0 <2019-02-15>`
* :feature:`0` DAQ_Scan: added the navigator option. It is a 2D area-like object where to define scans. All 2D scans in the current h5file
  are plotted in this area and at their corresponding position. Each scan plotability can be set.
* :bug:`0` DAQ_Scan: there was an error during the saving steps at the end of a scan preventing the h5file to flush properly
* :feature:`0` DAQ_Move_plugins: added the _controller_units parameter. Holds the native units used with the Move instance
* :release:`1.2.0 <2019-01-11>`
* :feature:`0` DAQ_Scan: Huge modification related to the scanning. Now you can select an area in one of the opened 2DViewers
  This viewer could for instance be a calibrated camera referring to the x and y positions of a XY stage. The Plot2D scan 2D viewer
  can also be used. Say that you just did a 2D scan and now you want to scan a cross-section within!!
  This area can be a 2D one (rectangle, 2D scan type) or a PolyLines (linked segments, 1D scan type). Random modes and
  others are still available in this mode
* :feature:`0` DAQ_Scan: possibility to save all datas in independent files or not (default is not)
* :feature:`0` DAQ_Scan: Overshoot configuration is now available: set DAQ_Move actions depending on detected values
* :release:`1.1.2 <2018-12-18>`
* :feature:`0` DAQ_Scan updated with averaging possibility. Opens up a new dock showing the current scan average. All scan in the average are saved
* :bug:`0` Corrected the background substraction in DAQ_Viewer
* :release:`1.1.1 <2018-12-18>`
* :bug:`0` Some wrong call to plugins in preset_manager
* :release:`1.1.0 <2018-12-18>`
* :feature:`0` removed plugins from tree structure. May be installed from github or pypi as external library
* :feature:`0` When started from DAQ_scan, all Quit pushbutton are disabled within individual Move and Viewer modules.
* :feature:`0` Moved the preset_mode folder out the pymodaq tree, but relative to HOMEPATH (windows) or HOME (linux & OSX) environment variable
* :release:`1.0.1 <2018-12-16>`
* :feature:`0` Tested entry-points after installation.*.exe files created successfully with manual setup install.
  But the link to working python is missing with pip install (python.exe and pythonw.exe) must be on the ``PATH``
* :bug:`0` Some wrong path to save/get preset modes
* :release:`1.0.0 <2018-12-10>`
* :feature:`0` Renamed all modules with lowercase. Renamed image viewer_multicolor as viewer2D


