.. _DAQ_Scan_module:

DAQ Scan
========

This module is the heart of PyMoDAQ, it will:

* help you declare the list of actuators and detectors to be used for a given experiment (:ref:`preset_manager`)
* setup automatic data acquisition of detectors as a function of one or more actuators
* save datas in hierarchical binary files

The flow of this module is as follow:

* at startup you have to define/load a preset (see :ref:`preset_manager`)
* A dataset will be declared the first time you set a scan. A dataset is equivalent to a single saved file
  containing multiple scans.  One can see a dataset as a set of scans related to single *subject of test*.
* Metadata can be saved for each dataset and then for each scan and be later retrieved from the saved file
  (see :ref:`saving_doc`)
* Performs multiple scans exploring all the parameters needed for your experiment


Introduction
------------

This module has a two windows,
one is a dashboard (:numref:`daq_scan_dashboard`) where a log and all declared actuators and detector
will be loaded as instances of DAQ_Move and DAQ_Viewer and
the other one is the main control window (see :numref:`daq_scan_main`).
The dashboard will give full control for manual adjustments
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move to
an automated scan using the main control window.


  .. _daq_scan_dashboard:

.. figure:: /image/DAQ_Scan/dashboard.png
   :alt: dashboard

   DAQ_Scan dashboard containing all declared modules and log.

.. :download:`png <dashboard.png>`

Main Control Window
-------------------
The main control window is comprised of a left panel for setting all parameters while the right panel will
dispay live data taken during the scan.

   .. _daq_scan_main:

.. figure:: /image/DAQ_Scan/main_ui.png
   :alt: daq_scan_main

   Main DAQ_Scan user interface.

.. :download:`png <main_ui.png>`

Scan Flow
*********
The top of the settings panel is comprised of buttons to set, start and stop a scan.

.. |start| image:: /image/DAQ_Scan/start_scan.png
    :width: 60pt
    :height: 20pt

.. |stop| image:: /image/DAQ_Scan/stop_scan.png
    :width: 60pt
    :height: 20pt

.. |quit| image:: /image/DAQ_Scan/quit.png
    :width: 60pt
    :height: 20pt

* |quit|: will shut down all modules and quit the application (redundant with: *File/Quit* menu)
* **Set Scan**: take into account the selected scan options and valid them or not. Gives also the number
  of steps for the currently set scan.
* **Set Ini. Positions**: will move all selected actuators to their initial positions as defined by the currently set scan.
* |start|: will start the currently set scan (first it will set it then start it)
* |stop|: stop the currently running scan.

Settings
********
The settings tree as shown on :numref:`daq_scan_main` contains everything needed to define a given scan,
save data and plot live information.

   .. _list_modules:

.. figure:: /image/DAQ_Scan/list_modules.png
   :alt: list_modules

   List of declared modules from a preset

.. :download:`png <list_modules.png>`

* **Moves/Detectors** (see :numref:`list_modules`)

  * **Moves**: list of all declared *DAQ_Move* modules (and present on the dashboard). One can select
    one or more modules for the current scan.
  * **Detectors** list of all declared *DAQ_Viewer* modules (and present on the dashboard). One can select
    one or more modules for the current scan.


* **Time Flow**

  * **Wait time**: extra time the application wait before moving on to the next DAQ_Move step. Enable
    rough cadencing if needed
  * **timeout**: raise a timeout if one of the selected modules is longer than timeout to respond

* **Scan options**:

  * **Scan type**: set the type of scan, 1D for a scan as a fucntion of only one actuator, 2D for a
    scan as a function of two actuators. Ohter options to come: *batch scan* (list of single scans to perform in a row)
    *point scan* (list of positions to scan from)
  * **Plot From**: select the detector from which data will be taken in order to plot live data
  * **Scan 1D settings**

    * **scan type**: either *linear* (usual scan) or *back to start* (the actuator comes back to the initial position
      after each linear step, for a reference measurement for instance). More to come if needed
    * **Start**: Initial position of the selected actuator (in selected actuator controller unit)
    * **Stop**: Last position of the scan (in selected actuator controller unit)
    * **Step**: Step size of the step (in selected actuator controller unit)
  * **Scan 2D settings**

    * **Scan type**: either *linear* (scan line by line), *linear back and forth* (scan line by line
      but in reverse direction each 2 lines) or *spiral* (start from the center and scan as a spiral)
    * **Start, Stop, Step**: for each axes (each actuators)
    * **Rmax, Rstep**: in case of spiral scan only. Rmax is the maximum radius of the spiral and Rstep is the radius increment.

* **Saving options**

  * **Save 2D datas**: if not selected, 2D datas will **not** be saved but only lineouts or integrated area (only in
    order to save memory space, but dangerous as you loose the possibility to get back initial raw data.
  * **Base path**: The folder where all datasets and scans will be saved, for instance: ``C:\Data``
  * **Base name**: the name given to the scans you are going to do (default is *Scan*)
  * **current path**: generated path to save infos on current scan, for instance: ``C:\Data\2018\20181226\Dataset_20181226_000\Scan000``
  * **current scan name**: indexed name from *base name*, for instance: ``Scan000``. Any scan from the current h5
    file can be selected here in order to add to it *comments*
  * **comments**: Other comments to add to the scan. Metadata can be entered before the scan but these
    *comments* can be added after, once one know if the scan is interesting or not for instance
  * **h5 file**: complete path of the current h5 file, for instance: ``C:\Data\2018\20181226\Dataset_20181226_000\Dataset_20181226_000.h5``

    * **Compression options**: by default data are compressed to mid level

      * **compression library**: see *pytables* package or *HDF5* documentation for details
      * **Compression level**: integer between 0 (no compression) and 9 (maximum compression)

Live data
*********

For a data acquisition system to be efficient, live data must be plotted in order to follow the
experiment behaviour and check if something is wrong or successfull without the need to perform
full data analysis. For this PyMoDAQ live data display will show all datas exported
by the setting **plot from** (defining which DAQ_Viewer module exports data). The total dimensionality of the datas + the scan dimensions
(1 for scan1D and 2 for Scan2D) should not exceed 2.

   .. _det1D:

.. figure:: /image/DAQ_Scan/1Ddetector.png
   :alt: 1Ddetector

   An example of a 1D detector having 2 channels. 0D data are generated as well from the integration of channel CH0
   within the red region of interest.


For instance, if the chosen detector is a 1D one, see :numref:`det1D`. Such a detector can generate various
type of live data:

* if the scan is 1D:

  * exported 0D datas will be displayed on the *1D Plot* tab as a line as a function of the actuator
    *position*, see :numref:`scan1D_0D`.
  * exported 1D datas will be displayed on the *2D Plot* tab as color levels as a function of the
    actuator *position*, see :numref:`scan1D_1D`.

   .. _scan1D_0D:

.. figure:: /image/DAQ_Scan/scan1D_0D.png
   :alt: scan1D_0D

   An example of a detector exporting 0D live data plotted as a function of the actuator *position*


   .. _scan1D_1D:

.. figure:: /image/DAQ_Scan/scan1D_1D.png
   :alt: scan1D_1D

   An example of a detector exporting 1D live data plotted as a function of the actuator *position*. Channel
   CH0 is plotted in red while channel CH1 is plotted in green.


* if the scan is 2D:

  * exported 0D datas will be displayed on the *2D Plot* tab as a pixel map where each pixel coordinates
    represents a scan coordinate. The color and intensity of the pixels refer to channels and data
    values, see :numref:`scan2D_0D` for a *spiral* 2D scan.

   .. _scan2D_0D:

.. figure:: /image/DAQ_Scan/scan2D_0D.png
   :alt: scan2D_0D

   An example of a detector exporting 0D live data plotted as a function of the 2 actuators's
   *position*. Integrated region of channel CH0 is plotted in red.

So at maximum, 2D dimensionality can be represented. In order to see live data from 2D detectors, one
should therefore export lineouts from ROIs or integrate data. All these operations are extremely simple
to perform using the ROI features of the data viewers (see :ref:`data_viewers`)


Preset manager
--------------

The *Preset modes* menu is used to create, modify and load preset. A preset is a set of
actuators and detectors represented in a tree like structure, see :ref:`preset_manager`.


.. _multiple_hardware:

Multiple hardware from one controller
-------------------------------------

Sometimes one hardware controller can drive multiple actuators and sometimes detectors (for instance a XY translation stage). For
this particular case the controller should not be initialized multiple times. One should identify one actuator
refered to as *Master* and the other ones will be referred to as *Slave*. They will share the same controller
address represented in the settings tree by the *Controller ID* entry. These settings will be activated
within the plugin script where one can define a unique identifier for each actuator (U or V for the conex
in :numref:`daq_move_gui_settings`). This feature can be enabled for both DAQ_Move and DAQ_Viewer modules but will be
most often encountered with actuators, so see for more details: :ref:`multiaxes_controller`.
