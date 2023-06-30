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
  (see :ref:`saving_doc` and :ref:`H5Browser_module`)
* Performs multiple scans exploring all the parameters needed for your experiment


Introduction
------------

This module has a main control window (see :numref:`daq_scan_main`).
The dashboard gives you full control for manual adjustments
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move to
an automated scan using the main control window.


Main Control Window
-------------------
The main control window is comprised of a left panel to set all parameters while the right panel will
display live data taken during a scan.

   .. _daq_scan_main:

.. figure:: /image/DAQ_Scan/main_ui.PNG
   :alt: daq_scan_main

   Main DAQ_Scan user interface.

.. :download:`png <main_ui.PNG>`

Scan Flow
*********
The top of the settings panel is comprised of buttons to set, start and stop a scan as well as quit the application.

.. |start| image:: /image/DAQ_Scan/start_scan.PNG
    :width: 60pt
    :height: 20pt

.. |stop| image:: /image/DAQ_Scan/stop_scan.PNG
    :width: 60pt
    :height: 20pt

.. |quit| image:: /image/DAQ_Scan/quit.PNG
    :width: 60pt
    :height: 20pt

* |quit|: will shut down all modules and quit the application (redundant with: *File/Quit* menu)
* **Set Scan**: take into account the selected scanner settings and valid them or not.
* **Init. Positions**: will move all selected actuators to their initial positions as defined by the currently set scan.
* |start|: will start the currently set scan (first it will set it then start it)
* |stop|: stop the currently running scan (in case of a batch of scans, it will skips the current one).

Menu Bar Description
********************
There are two entries in the menu bar: *File* and *Settings*

The *File* entry will let you:

* load a previously saved scan file (and keep saving scans on it)
* Save the current file in another filename than the default one
* Load the content of the current file into the *H5Browser*

The *Settings* entry will let you:

* display the *Navigator* see :ref:`navigator_paragrah`
* Display and activate the *Scan Batch Manager*

.. _settings_paragraph:

Settings
********
The settings tree as shown on :numref:`daq_scan_main` is actually divided in a few subtrees that contain everything
needed to define a given scan, save data and plot live information.


Module Manager
++++++++++++++

The leftmost tree is the user interface of the module manager (see :ref:`module_manager` for details). It allows the user
to select the actuators and detectors for the next scan (see :numref:`list_modules`). This interface is also used for the
DAQ_Logger extension.

   .. _list_modules:

.. figure:: /image/DAQ_Scan/list_modules.PNG
   :alt: list_modules

   List of declared modules from a preset

.. :download:`png <list_modules.PNG>`

General Settings
++++++++++++++++

The General Settings are comprised of (see :numref:`general_settings_fig`):

* **Time Flow**

  * **Wait time**: extra time the application wait before moving on to the next scan step. Enable
    rough cadencing if needed
  * **timeout**: raise a timeout if one of the scan step (moving or detecting) is taking a longer time than timeout to respond

* **Scan options** :

  * **N average**: Select how many set scans to perform. Save all individual scans and its average
  * **Plot From**: select the detector from which data will be taken in order to plot live data


   .. _general_settings_fig:

.. figure:: /image/DAQ_Scan/general_settings.PNG
   :alt: list_modules

   General settings for the DAQ_Scan module


Saving: Dataset and scans
+++++++++++++++++++++++++

DAQ_Scan module will save your data in **datasets**. Each **dataset** is a unique h5 file and may contain multiple scans. The
idea behind this is to have a unique file for a set of related data (the **dataset**) together with all the meta information:
logger data, module parameters (settings, ROI...) even *png* screenshots of the various panels.

:numref:`figure_h5browser_data` displays the content of a typical **dataset** file containing various scans and how each data
and metadata is used by the H5Browser to display the info to the user.

   .. _figure_h5browser_data:

.. figure:: /image/Utils/h5browser_datas.PNG
   :alt: h5 browser

   h5 browser and arrows to explain how each data or metadata is being displayed


The Save Settings (see :numref:`save_settings_fig`) is the user interface of the :ref:`h5saver_module`, it is a general
interface to parametrize data saving in the hdf5 file:

   .. _save_settings_fig:

.. figure:: /image/DAQ_Scan/save_settings.PNG
   :alt: list_modules

   Save settings for the DAQ_Scan extension


In order to save correctly your datas in custom applications, a utility module is to be used: pymodaq.utils.h5saver,
it will save scans and datas following the rules


Scanner
*******

Finally all specifics of the upcoming scan are configured using the :ref:`scanner_paragrah` module interface as seen on
:numref:`scan2D_fig2` in the case of an adaptive Scan2D scan configuration.

  .. _scan2D_fig2:

.. figure:: /image/managers/scanner_widget.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Scan2D* scan type and an *adaptive* scan subtype and its particular settings.


Live data
*********

For a data acquisition system to be efficient, live data must be plotted in order to follow the
experiment behaviour and check if something is wrong or successfull without the need to perform
full data analysis. For this PyMoDAQ live data display will show all datas exported
by the setting **plot from** (defining which DAQ_Viewer module exports data). The total dimensionality of the datas + the scan dimensions
(1 for scan1D and 2 for Scan2D) should not exceed 2 (this means one cannot plot more complex plots than 2D intensity plots).

   .. _det1D:

.. figure:: /image/DAQ_Scan/1Ddetector.PNG
   :alt: 1Ddetector

   An example of a 1D detector having 2 channels. 0D data are generated as well from the integration of channel CH0
   within the cyan region of interest (ROI_00).


For instance, if the chosen detector is a 1D one, see :numref:`det1D`. Such a detector can generate various
type of live data. It will export the raw 1D data and integrated 0D data within the declared ROI, then:

* if the scan is 1D:

  * exported 0D datas will be displayed on the *1D Plot* tab as a line as a function of the actuator
    *position*, see :numref:`scan1D_0D`.
  * exported 1D datas will be displayed on the *2D Plot* tab as color levels as a function of the
    actuator *position*, see :numref:`scan1D_1D`.

   .. _scan1D_0D:

.. figure:: /image/DAQ_Scan/scan1D_0D.PNG
   :alt: scan1D_0D

   An example of a detector exporting 0D live data plotted as a function of the actuator *position*


   .. _scan1D_1D:

.. figure:: /image/DAQ_Scan/scan1D_1D.PNG
   :alt: scan1D_1D

   An example of a detector exporting 1D live data plotted as a function of the actuator *position*. Channel
   CH0 is plotted in red while channel CH1 is plotted in green.


* if the scan is 2D:

  * exported 0D datas will be displayed on the *2D Plot* tab as a pixel map where each pixel coordinates
    represents a scan coordinate. The color and intensity of the pixels refer to channels and data
    values, see :numref:`scan2D_0D` for a *spiral* 2D scan.

   .. _scan2D_0D:

.. figure:: /image/DAQ_Scan/scan2D_0D.PNG
   :alt: scan2D_0D

   An example of a detector exporting 0D live data plotted as a function of the 2 actuators's
   *position*. Integrated region of channel CH0 is plotted in red.

So at maximum, 2D dimensionality can be represented. In order to see live data from 2D detectors, one
should therefore export lineouts from ROIs or integrate data. All these operations are extremely simple
to perform using the ROI features of the data viewers (see :ref:`data_viewers`)




.. _navigator_paragrah:

Navigator
---------

From version 1.4.0, a new module has been added: the Navigator (daq_utils.plotting.navigator). It is most useful when
dealing with 2D scans such as XY
cartography. As such, it is not displayed by default. It consists of a tree like structure displaying all
currently saved 2D scans (in the current dataset) and a viewer where selected scans can be displayed at their respective
locations. It can be displayed using the *Settings* menu, *Show Navigator* option. :numref:`navigator` shows the DAQ_scan extension
with activated Navigator and a few scans. This navigator can also be used as a :ref:`scan_selector_paragraph` viewer to
quickly explore and select areas to scan on a 2D phase space.

   .. _navigator:

.. figure:: /image/DAQ_Scan/navigator.PNG
   :alt: navigator

   An example of dataset displaying several 2D scans at their respective locations (up and right axis)


Scan Batch Manager
------------------

If the *Scan Batch Manager* is activated, a new menu entry will appear: *Batch Configs*, that let the user
define, modify or load scan batch configurations. When loaded, a particular configuration will
be displayed in the batch window. This window (see :numref:`scanbatch`) displays (in a tree) a list of scans to perform.
Each scan is defined by a set of actuators/detectors to use and scan settings (*Scan1D*, *Linear*... just as described in
:ref:`settings_paragraph`).

   .. _scanbatch:

.. figure:: /image/DAQ_Scan/scanbatch.png
   :alt: scanbatch

   An example of a Scan Batch configuration displaying several scans to perform

A new start button |startbatch| will also appear on the main window to start the currently loaded
scan batch.

.. |startbatch| image:: /image/DAQ_Scan/start_scanbatch.PNG
    :width: 20pt
    :height: 20pt