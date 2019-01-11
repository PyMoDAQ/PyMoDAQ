:orphan:

=========
Changelog
=========
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


