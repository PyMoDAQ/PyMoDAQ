.. _DAQ_Scan_module:


DAQ Scan
========


This module is an extension of the DashBoard but is the heart of PyMoDAQ, it will:

* setup automatic data acquisition of detectors as a function of one or more actuators
* save datas in hierarchical hdf5 binary files (compatible with the :ref:`H5Browser_module` used to display/explore
  data)

The flow of this module is as follow:

* at startup you have to define/load a preset (see :ref:`preset_manager`) in the Dashboard
* Select DAQ_Scan in the actions menu
* A dataset will be declared the first time you set a scan. A dataset is equivalent to a single saved file
  containing multiple scans.  One can see a dataset as a series of scans related to single *subject/sample to be characterized*.
* Metadata can be saved for each dataset and then for each scan and be later retrieved from the saved file
  (see :ref:`module_savers` and :ref:`H5Browser_module`)
* Performs multiple scans exploring all the parameters needed for your experiment


.. toctree::
   :numbered:
   :maxdepth: 3
   :caption: Contents:

   daq_scan_main
   scanner
   navigator
   scan_batch


