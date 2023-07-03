


Introduction
------------
The dashboard gives you full control for manual adjustments (using the UI)
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move to
an automated scan using the main control window of the ``DAQ_Scan``, see :numref:`daq_scan_main`.


.. |start| image:: /image/DAQ_Scan/start_scan.PNG
    :width: 60pt
    :height: 20pt

.. |get_data| image:: /image/DAQ_Scan/get_data.PNG
    :width: 60pt
    :height: 20pt

.. |stop| image:: /image/DAQ_Scan/stop_scan.PNG
    :width: 60pt
    :height: 20pt

.. |quit| image:: /image/DAQ_Scan/quit.PNG
    :width: 60pt
    :height: 20pt

.. |goto| image:: /image/DAQ_Scan/go_to.PNG
    :width: 20pt
    :height: 20pt

.. |log| image:: /image/DAQ_Scan/log.PNG
    :width: 20pt
    :height: 20pt


Main Control Window
-------------------
The main control window is comprised of various panels to set all parameters and
display live data taken during a scan.

   .. _daq_scan_main:

.. figure:: /image/DAQ_Scan/main_ui.PNG
   :alt: daq_scan_main

   Main DAQ_Scan user interface.

.. :download:`png <main_ui.PNG>`


*  The *instrument selection* panel allows to quickly select the detectors and the actuators to use for the next scan
*  The *settings panel* is divided in three sections (see :ref:`settings_paragraph` for more details):

   *  Scanner settings: select and set the next scan type and values.
   *  General settings: options on timing, scan averaging and plotting.
   *  Save settings: everything about what should be saved, how and where.
*  The *Live plots selection* panel allows to select which data produced from selected detectors should be rendered live
*  The *Live Plots* panels renders the data as a function of varying parameters as selected in the *Live plots selection*
   panel

Scan Flow
---------

Performing a scan is typically done by:

* Selecting which detectors to save data from
* Selecting which actuators will be the scan varying parameters
* Selecting the type of scan (see :ref:`daq_scan_scanner`): 1D, 2D, ... and subtypes
* For a given type and subtype, settings the start, stop, ... of the selected actuators
* Selecting data to be rendered live (none by default)
* Starting the scan


Selecting detectors and actuators
+++++++++++++++++++++++++++++++++

The *Instrument selection* panel is the user interface of the module manager (see :ref:`module_manager` for details).
It allows the user to select the actuators and detectors for the next scan (see :numref:`list_modules`). This interface
is also used for the ``DAQ_Logger`` extension.

   .. _list_modules:

.. figure:: /image/DAQ_Scan/list_modules.PNG
   :alt: list_modules

   List of declared modules from a preset

.. :download:`png <list_modules.PNG>`


.. _daq_scan_scanner:

Selecting the type of scan
++++++++++++++++++++++++++

All specifics of the upcoming scan are configured using the :ref:`scanner_paragrah` module interface as seen on
:numref:`scan2D_fig2` in the case of a spiral Scan2D scan configuration.

  .. _scan2D_fig2:

.. figure:: /image/managers/scanner_widget.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Scan2D* scan type and an *adaptive* scan subtype and its particular settings.


Selecting the data to render live
+++++++++++++++++++++++++++++++++

For a data acquisition system to be efficient, live data must be plotted in order to follow the
experiment behaviour and check if something is going wrong or successfully without the need to perform a
full data analysis. For this PyMoDAQ live data display will allows the user to select data to be plotted from
the selected detectors.

The list of all possible data to be plotted can be obtained by clicking on the |get_data| button. All data will
be classified by dimensionality (0D, 1D). The total dimensionality of the data + the scan dimensions
(1 for scan1D and 2 for Scan2D...) should not exceed 2 (this means one cannot plot more complex plots than 2D intensity
plots). It also means that you should use ROI to generate lower dimensionality data from your raw data for a proper
live plot.

For instance, if the chosen detector is a 1D one, see :numref:`det1D`. Such a detector can generate various
type of live data.

   .. _det1D:

.. figure:: /image/DAQ_Scan/1Ddetector.PNG
   :alt: 1Ddetector

   An example of a 1D detector having 2 channels. 0D data are generated as well from the integration of channel CH0
   within the regions of interest (ROI_00 and ROI_01).


It will export the raw 1D data and the 1D lineouts and integrated 0D data from the declared ROI as shown
on :numref:`det1D_data_probe`


   .. _det1D_data_probe:

.. figure:: /image/DAQ_Scan/1Ddetector_data.PNG
   :alt: 1Ddetector_data

   An example of all data generated from a 1D detector having 2 channels. 0D data and 1D data are generated
   as well from the
   integration of channel CH0 within the regions of interest (ROI_00 and ROI_01).

Given these constraints, one live plot panel will be created by selected data to be rendered with some
specificities. One of these is that by default, all 0D data will be grouped on a single viewer panel,
as shown on :numref:`daq_scan_main` (this can be changed using the :ref:`general_settings_daq_scan`)

The viewer type will be chosen (Viewer1D or 2D) given the dimensionality of the data to be ploted and the number
of selected actuators.

* if the scan is 1D:

  * exported 0D datas will be displayed on a ``Viewer1D`` panel as a line as a function of the actuator
    *position*, see :numref:`daq_scan_main`.
  * exported 1D datas will be displayed on a ``Viewer2D`` panel as color levels as a function of the
    actuator *position*, see :numref:`scan1D_1D`.

   .. _scan1D_1D:

.. figure:: /image/DAQ_Scan/scan1D_1D.PNG
   :alt: scan1D_1D
   :figwidth: 500 px

   An example of a detector exporting 1D live data plotted as a function of the actuator *position*. Channel
   CH0 is plotted in red while channel CH1 is plotted in green.


* if the scan is 2D:

  * exported 0D datas will be displayed on a ``Viewer2D`` panel as a pixel map where each pixel coordinates
    represents a scan coordinate. The color and intensity of the pixels refer to channels and data
    values, see :numref:`scan2D_0D` for a *linear* 2D scan.

   .. _scan2D_0D:

.. figure:: /image/DAQ_Scan/scan2D_0D.PNG
   :alt: scan2D_0D
   :figwidth: 500 px

   An example of a detector exporting 0D live data plotted as a function of the 2 actuators's
   *position*. Integrated regions of channel CH0 are plotted in red and green.

So at maximum, 2D dimensionality can be represented. In order to see live data from 2D detectors, one
should therefore export lineouts from ROIs or integrate data. All these operations are extremely simple
to perform using the ROI features of the data viewers (see :ref:`data_viewers`)


Various settings
----------------

Toolbar
+++++++
The toolbar is comprised of buttons to start and stop a scan as well as quit the application. Some other functionalities
can also be triggered with other buttons as described below:



* |quit|: will shut down all modules and quit the application (redundant with: *File/Quit* menu)
* **Init. Positions**: will move all selected actuators to their initial positions as defined by the currently set scan.
* |start|: will start the currently set scan (first it will set it then start it)
* |stop|: stop the currently running scan (in case of a batch of scans, it will skips the current one).
* |goto|: when checked, allows currently actuators to be moved by double clicking on a position in the live plots
* |log|: opens the logs in a text editor

Menu Bar Description
++++++++++++++++++++
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
++++++++
The settings tree as shown on :numref:`daq_scan_main` is actually divided in a few subtrees that contain everything
needed to define a given scan, save data and plot live information.


.. _general_settings_daq_scan:

General Settings
****************

The General Settings are comprised of:

* **Time Flow**

  * **Wait time step**: extra time the application wait before moving on to the next scan step. Enable
    rough timing if needed
  * **Wait time between**: extra time the application wait before starting a detector's grab after the actuators
    reached their final value.
  * **timeout**: raise a timeout if one of the scan step (moving or detecting) is taking a longer time than timeout to respond

* **Scan options** :

  * **N average**: Select how many scans to average. Save all individual scans.

* **Scan options** :
  * **Get Data** probe selected detectors to get info on the data they are generating (including processed data from ROI)
  * **Group 0D data**: Will group all generated 0D data to be plotted on the same viewer panel (work only for 0D data)
  * **Plot 0D** shows the list of data that are 0D
  * **Plot 1D** shows the list of data that are 1D
  * **Prepare Viewers** generates viewer panels depending on the selected data to be live ploted
  * **Plot at each step**

    * if checked, update the live plots at each step in the scan
    * if not, display a **Refresh plots** integer parameter, say T. Will update the live plots every T milliseconds

*  **Save Settings**: See :ref:`h5saver_settings`


.. _daq_scan_saving:

Saving: Dataset and scans
*************************

DAQ_Scan module will save your data in **datasets**. Each **dataset** is a unique h5 file and may contain multiple scans. The
idea behind this is to have a unique file for a set of related data (the **dataset**) together with all the meta information:
logger data, module parameters (settings, ROI...) even *png* screenshots of the various panels.

:numref:`figure_h5browser_data` displays the content of a typical **dataset** file containing various scans and how each data
and metadata is used by the :ref:`H5Browser_module` to display the info to the user.

   .. _figure_h5browser_data:

.. figure:: /image/Utils/h5browser_datas.PNG
   :alt: h5 browser

   h5 browser and arrows to explain how each data or metadata is being displayed


The Save Settings (see :numref:`save_settings_fig`) is the user interface of the :ref:`h5saver_module`, it is a general
interface to parametrize data saving in the hdf5 file:

   .. _save_settings_fig:

.. figure:: /image/Utils/h5saver_settings.PNG
   :alt: list_modules

   Save settings for the DAQ_Scan extension


In order to save correctly your datas, saving modules are to be used, see :ref:`module_savers`.
