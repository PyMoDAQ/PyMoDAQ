Introduction
------------
The dashboard gives you full control for manual adjustments (using the UI)
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move to
an automated scan using the main control window of the ``DAQ_Scan``, see :numref:`daq_scan_main`.


Main Control Window
-------------------
The main control window is comprised of various toolbars, a *Scan Command* panel to set all parameters and
dockable panels displaying live data taken during a scan.

   .. _daq_scan_main:

.. figure:: /image/DAQ_Scan/scan_main_ui.png
   :alt: daq_scan_main

   Main DAQ_Scan user interface at the end of a 1D scan. Left: the *Scan Command* panel with the *Instrument
   selection* (top left), the *Plotting options* (bottom left) and the *Scanner Settings* (center); the
   *General Settings* and *Save Settings* are collapsed below them. Right: the live plots.


*  The toolbars (top) allow to start, stop and pause a scan, see :ref:`daq_scan_toolbar`
*  The *Instrument selection* panel allows to quickly select the detectors and the actuators to use for the next scan
*  The *Scanner Settings* panel allows to select the type of scan and to set its values
*  The *Plotting options* panel allows to select which data produced from the selected detectors should be rendered
   live (these are the *Live plots selection* options)
*  The *General Settings* and *Save Settings* sections (see :ref:`settings_paragraph` for more details):

   *  General settings: options on timing, scan averaging and plotting.
   *  Save settings: everything about what should be saved, how and where.
*  The live plots panels render the data as a function of the varying parameters, as selected in the *Plotting
   options*. They can be moved, resized or detached like any other dock.

Scan Flow
---------

Performing a scan is typically done by:

* Selecting which detectors to save data from
* Selecting which actuators will be the scan varying parameters
* Selecting the type of scan (see :ref:`daq_scan_scanner`): 1D, 2D, ... and subtypes
* For a given type and subtype, setting the start, stop, ... of the selected actuators
* Selecting data to be rendered live (nothing is listed until you ask for it)
* Starting the scan with the **Start** button of the toolbar (**Stop** ends it, **Pause** suspends it)


Selecting detectors and actuators
+++++++++++++++++++++++++++++++++

The *Instrument selection* panel is the user interface of the module manager (see :ref:`module_manager` for details).
It lists the detectors and the actuators declared in the experiment loaded in the Dashboard and allows the user to
select the ones for the next scan by ticking them (see :numref:`list_modules`). The *Probe detectors* and
*Probe actuators* rows can be used to check that the selected modules respond (the LED turns green when they do).
This interface is also used for the ``DAQ_Logger`` extension.

   .. _list_modules:

.. figure:: /image/DAQ_Scan/scan_instruments.png
   :alt: list_modules

   List of declared modules from an experiment, with two detectors and one actuator selected.


.. _daq_scan_scanner:

Selecting the type of scan
++++++++++++++++++++++++++

All specifics of the upcoming scan are configured using the :ref:`scanner_paragraph` module interface, as seen on
:numref:`scan2D_fig2` in the case of a Scan2D scan configuration. Once the actuators are selected, choose the scan
type (1D, 2D, ...), its subtype (linear, adaptive, ...) and set the start, stop and step values of each actuator.

  .. _scan2D_fig2:

.. figure:: /image/DAQ_Scan/scan_scanner2D.png
   :alt: scanner_fig

   The Scanner user interface set on a *Scan2D* scan type and a *Linear* scan subtype with two actuators (*Theta*
   and *Xaxis*), 100 steps in total.


Selecting the data to render live
+++++++++++++++++++++++++++++++++

For a data acquisition system to be efficient, live data must be plotted in order to follow the
experiment behaviour and check if something is going wrong or successfully without the need to perform a
full data analysis. For this PyMoDAQ live data display will allows the user to select data to be plotted from
the selected detectors.

The list of all possible data to be plotted can be obtained by clicking on the **Get data** button of the *Plotting
options*. The selected detectors are probed (a snap is done) and all the data they generate are listed and classified by
dimensionality (0D, 1D). They are all ticked by default: untick what should not be plotted. The total dimensionality
of the data + the scan dimensions (1 for scan1D and 2 for Scan2D...) should not exceed 2 (this means one cannot plot
more complex plots than 2D intensity plots). It also means that you should use ROI to generate lower dimensionality data
from your raw data for a proper live plot.

For instance, if the chosen detector is a 1D one, see :numref:`det1D`. Such a detector can generate various
type of live data.

   .. _det1D:

.. figure:: /image/DAQ_Scan/scan_det1D_viewer.png
   :alt: 1Ddetector

   An example of a 1D detector having 2 channels. A region of interest (ROI_00) has been defined on channel CH00: its
   integration (0D data) is plotted in the lower panel.


It will export the raw 1D data and the 1D lineouts and integrated 0D data from the declared ROI as shown
on :numref:`det1D_data_probe`


   .. _det1D_data_probe:

.. figure:: /image/DAQ_Scan/scan_plot_options.png
   :alt: 1Ddetector_data

   The *Plotting options* after clicking on **Get data** with a 0D and a 1D detector selected. The 0D data (*Plot 0Ds*)
   are the one of the 0D detector and the integration of the ROI of the 1D detector. The 1D data (*Plot 1Ds*) are the raw
   data of the 1D detector and the lineout of its ROI.

Once the data to plot are selected, click on **Prepare Viewers** to generate the live plot panels (this is also done
when starting a scan). One live plot panel will be created by selected data to be rendered with some
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

.. figure:: /image/DAQ_Scan/scan_live1D_1D.png
   :alt: scan1D_1D
   :figwidth: 500 px

   An example of a detector exporting 1D live data (the lineout of the ROI) plotted as a function of the actuator
   *position*. Channel CH0 is plotted in red while channel CH1 is plotted in green.


* if the scan is 2D:

  * exported 0D datas will be displayed on a ``Viewer2D`` panel as a pixel map where each pixel coordinates
    represents a scan coordinate. The color and intensity of the pixels refer to channels and data
    values, see :numref:`scan2D_0D` for a *linear* 2D scan.

   .. _scan2D_0D:

.. figure:: /image/DAQ_Scan/scan_live2D_0D.png
   :alt: scan2D_0D
   :figwidth: 500 px

   An example of a detector exporting 0D live data (the integrated ROI of a 1D detector) plotted as a function of the
   2 actuators's *position*.

So at maximum, 2D dimensionality can be represented. In order to see live data from 2D detectors, one
should therefore export lineouts from ROIs or integrate data. All these operations are extremely simple
to perform using the ROI features of the data viewers (see :ref:`data_viewers`)


Various settings
----------------

.. _daq_scan_toolbar:

Toolbar
+++++++
The scan toolbar (see :numref:`daq_scan_toolbar_fig`) is comprised of buttons to start, pause and stop a scan. Some other
functionalities can also be triggered with other buttons as described below:

   .. _daq_scan_toolbar_fig:

.. figure:: /image/DAQ_Scan/scan_toolbar.png
   :alt: scan toolbar

   The scan toolbar and the *Scan Manager* toolbar.

* **Start**: will start the currently set scan (first it will set it then start it)
* **Stop**: stop the currently running scan
* **Pause**: toggle pause/resume on a running scan. The scan loop will wait until unpaused or stopped.
* **Init. Positions**: will move all selected actuators to their initial positions as defined by the currently set scan.
* **Move at double clicked**: when checked, allows currently selected actuators to be moved by double clicking on a
  position in the live plots

The top toolbar, shared with the Dashboard, allows to quit the application (red cross: it will shut down all modules,
redundant with the *File/Quit* menu), to show the Dashboard and to load an experiment or a state. The *Actions* menu
duplicates the actions of the scan toolbar.

Menu Bar Description
++++++++++++++++++++
There are two entries in the menu bar: *File* and *Settings*

The *File* entry will let you:

* Load a previously saved scan file (and keep saving scans on it)
* Save the current file in another filename than the default one
* Load the content of the current file into the *H5Browser*
* Open / Close the current h5 file (useful to release the file lock or reopen after closing)

The *Settings* entry will let you:

* display the *Navigator* see :ref:`navigator_paragrah`
* Display and activate the *Scan Batch Manager*

Status Bar
++++++++++
The status bar at the bottom of the window shows:

* A message label with the current file name and scan name
* Scan step counters (total steps and current step)
* A **Scan done** LED indicator
* A **File** LED indicator (green when the h5 file is open)
* An **SWMR** label that shows:

  * *SWMR* when SWMR mode is actively in use during a scan
  * *SWMR file* when the opened file was created with SWMR support but SWMR is not currently active
  * hidden when the file has no SWMR association



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

* **Scan options** :

  * **N average**: Select how many scans to average. Save all individual scans.
  * **Go to ini. positions**: when checked (default), actuators are moved back to their initial positions
    when the scan ends or is stopped.

* **Plotting options** :
  * **Get Data** probe selected detectors to get info on the data they are generating (including processed data from ROI)
  * **Group 0D data**: Will group all generated 0D data to be plotted on the same viewer panel (work only for 0D data)
  * **Plot 0D** shows the list of data that are 0D
  * **Plot 1D** shows the list of data that are 1D
  * **Prepare Viewers** generates viewer panels depending on the selected data to be live ploted
  * **Plot at each step**

    * if checked, update the live plots at each step in the scan
    * if not, display a **Refresh plots** integer parameter, say T. Will update the live plots every T milliseconds

*  **Save Settings**: See :ref:`h5saver_module`


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
