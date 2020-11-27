Utility Modules
===============

.. toctree::
   :maxdepth: 3
   :caption: Contents:


Introduction
------------

Utility modules are used within each main modules of PyMoDAQ but can also be used as building
blocks for custom application. In that sense, all :ref:`data_viewers` and even :ref:`DAQ_Viewer_module` and
:ref:`DAQ_Move_module` can be used as building blocks to control actuators and display datas in a
custom application.

.. _module_manager:

Module Manager
--------------

The module manager is an object used to deal with:

* Selection of actuators and detectors by a user (and internal facilities to manipulate them, see the API when it will be written...)
* Synchronize acquisition from selected detectors
* Synchronize moves from selected actuators
* Probe as lists all the datas that will be exported by the selected detectors (see :numref:`module_managerfig`)
* Test Actuators positioning. Clicking on test_actuator will let you enter positions for all selected actuators that
  will be displayed when reached


  .. _module_managerfig:

.. figure:: /image/managers/module_manager.PNG
   :alt: module_manager_fig

   The Module Manager user interface with selectable detectors and actuators, with probed data feature and actuators testing.



.. _scanner_paragrah:

Scanner
-------

The *Scanner* module is an object dealing with configuration of scan modes and is mainly used by the DAQ_Scan extension.
It features a graphical interface, see :numref:`scan2D_fig`, allowing the configuration of the scan type and all its
particular settings. The **Scan type** sets the type of scan, **Scan1D** for a scan as a function of only one actuator,
**Scan2D** for a scan as a function of two actuators, **Sequential** for scans as a function of 1, 2...N actuators and
**Tabular** for a list of points coordinates in any number of actuator phase space. All specific features of these scan
types are described below:

Scan1D
++++++

The possible settings are visible on :numref:`scan1D_fig` and described below:

* **scan subtype**: either *Linear* (usual uniform 1D scan), *Back to start* (the actuator comes back to the initial position
  after each linear step, for a referenced measurement for instance), *Random* same as *Linear* except the
  predetermined positions are sampled randomly and from version 2.0.1 *Adaptive* that features no predetermined
  positions. These will be determined by an algorithm influenced by the signal returned from a detector on the
  previously sampled positions (see :ref:`adaptive_scans`)
* **Start**: Initial position of the selected actuator (in selected actuator controller unit)
* **Stop**: Last position of the scan (in selected actuator controller unit)
* **Step**: Step size of the step (in selected actuator controller unit)

For the special case of the Adaptive mode, one more feature is available: the *Loss type**. It modifies the algorithm
behaviour (see :ref:`adaptive_scans`)

  .. _scan1D_fig:

.. figure:: /image/managers/scanner_widget_1D.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Scan1D* scan type and the visible list of scan subtype.



Scan2D
++++++

The possible settings are visible on :numref:`scan2D_fig` and described below:

  .. _scan2D_fig:

.. figure:: /image/managers/scanner_widget.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Scan2D* scan type and a *Spiral* scan subtype and its particular settings.


* **Scan subtype**: See :numref:`scan2D_subtypes` either *linear* (scan line by line), *linear back and forth* (scan line by line
  but in reverse direction each 2 lines), *spiral* (start from the center and scan as a spiral), *Random* (random
  sampling of the *linear* case) and *Adaptive* (see :ref:`adaptive_scans`)
* **Start, Stop, Step**: for each axes (each actuators)
* **Rmax, Rstep, Npts/axis**: in case of spiral scan only. Rmax is the maximum radius of the spiral (calculated),
  and Npts/axis is the number of points for both axis (total number of points is therefore Npts/axis²).
* **Selection**: see :ref:`scan_selector_paragraph`


  .. _scan2D_subtypes:

.. figure:: /image/DAQ_Scan/scan2D_subtypes.png
   :alt: scannersubtypes_fig

   The main Scan2D subtypes: Linear, Back and Forth and Spiral.




Sequential
++++++++++

The possible settings are visible on :numref:`scan_seq_fig` and described below:

* **Scan subtype**: only *linear* this means the scan have a sequence of Scan1D of the last specified actuator
  (on :numref:`scan_seq_fig`, it is *Xaxis*) for all positions of the last but end actuator (here *Yaxis*) and so on. So on
  :numref:`scan_seq_fig` there will be 11 steps for *Xaxis* times 11 steps for *Yaxis* times 10 steps for *Theta axis*
  so in total 11x11x10=1210 total steps for this 3 dimensions scan.

.. note::

  If only 1 actuator is selected, then the Sequential scan is identical to the *Scan1D* scan but where only the *linear*
  subtype is available. If 2 actuators are selected, then the Sequential scan is identical to the *Scan2D* scan but
  where only the *linear* subtype is available.


  .. _scan_seq_fig:

.. figure:: /image/managers/scanner_widget_sequential.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Sequential* scan type with a sequence of three actuators


Tabular
+++++++

The tabular scan type consists of a list of positions (for each selected actuators).

Tabular Linear/Manual case
##########################
In the Linear/Manual case, the module will
move actuators on each positions and grab datas. On :numref:`scan_tabular_fig`, a list of 79 positions has been set.
By right clicking on the table, a context manager pops up and gives the possibility to:

* add one more position in the list
* remove the selected position
* clear all the positions
* load positions from a text file (as many columns as selected actuators with their positions separated by a tab)
* save the current list of positions in a text file (for later quick loading of positions)

One can also drag and drop elements of the list at a different index in the list.

  .. _scan_tabular_fig:

.. figure:: /image/managers/scanner_widget_tabular.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Tabular* scan type with a list of points for 2 actuators. A context menu with
   other options is also visible (right click on the table to show it)

Tabular Linear/Polylines case
#############################

In the particular case of 2 selected actuators, it could be more interesting to draw the positions for the tabular scan.
One possibility is to draw segments on a 2D viewer (see :numref:`scan_selector`) and positions will be points along
these segments (it will be a kind of 1D cuts within a 2D phase space). A new setting, *Curvilinear step*  appears. The
positions will be points starting from the start of the first segment and then step along them by the value of this setting.
That gives, for :numref:`scan_selector`, 40 points defined along the segments.

   .. _scan_selector:

.. figure:: /image/DAQ_Scan/scan_selector.PNG
   :alt: scan_selector

   An example of 1D complex sections selected within a 2D area

Tabular Adaptive case
#####################

**Valid for 1 or 2 selected actuators**. The tabular adaptive case will be similar to scan1D adaptive mode, except that one
adaptive Scan1D will be done for each segments defined by the list of positions in the table. For instance,
:numref:`scan_tabular_adaptive_fig` shows a list of 4 positions defining 4 segments in a 2D space. The adaptive scan will
be done on/along these 4 segments. Positions can be set manually or from a *Polylines* selection as seen on :numref:`scan_selector`.


  .. _scan_tabular_adaptive_fig:

.. figure:: /image/managers/scanner_widget_tabular_adaptive.PNG
   :alt: scanner_fig

   The Scanner user interface set on a *Tabular* scan type with a list of points for 2 actuators. A context menu with
   other options is also visible (right click on the table to show it)


.. _adaptive_scans:

Adaptive
++++++++


All the adaptive features are using the `python-adaptive`__ package (Parallel active learning of
mathematical functions, 10.5281/zenodo.1182437). And the reader is invited to explore their tutorials to discover how
these algorithms work. In PyMoDAQ the `learner1D`__ algorithm is used for the *Scan1D and Tabular* scan types while the
`learner2D`__ one is used for *Scan2D* scan type.

Bounds
######
As a general rule, the adaptive algorithm will need bounds to work with. For *Scan1D* scan type, these will be defined
from the *start* and *stop* settings. For *Tabular*, it is the start and ends of the segments. Finally for *Scan2D*, it
is the: *Start Ax 1*, *Stop Ax 1* and *Start Ax 2*, *Stop Ax 2* that are defining scan bounds.

Feedback
########

The adaptive algorithm will need for each probed positions a feedback value telling it the fitness of the probed points.
From these on all previous points, it will determine the best next points to probe. In order to provide such a feedback,
on has to choose a signal among all available from the DashBoard detectors. It has to be a Scalar so originate from a 0D
detector or integrated ROI from 1D or 2D detectors. The module manager user interface (right most setting tree in the
DAQ_Scan module ,see :numref:`module_managerfig`) will let you probe available datas exported from currently selected
detectors. You can then pick the Data0D one you want to use as the Adaptive feedback. For instance, on :numref:`module_managerfig`,
three Data0D are available, one from a 0D detector (CH000) and 2 from the Measurements ROIs of a 1D detector. In that case the
CH000 data has been selected and will therefore be use as feedback for the Adaptive algorithm.

Loss
####

All the Adaptive options are called *Loss* on the Scanner UI. These influence the adaptive algorithm, using previously
probed positions and their feedback to guess the next point to probe. See the `Adaptive documentation`__ on *loss*
to understand all the possibilities.

__ https://adaptive.readthedocs.io/en/latest/
__ https://adaptive.readthedocs.io/en/latest/tutorial/tutorial.Learner1D.html
__ https://adaptive.readthedocs.io/en/latest/tutorial/tutorial.Learner2D.html
__ https://adaptive.readthedocs.io/en/latest/tutorial/tutorial.custom_loss.html

.. _scan_selector_paragraph:

Scan Selector
+++++++++++++

Scans can be specified manually using the *Scanner Settings* (explained above). However, in the case of a scan using 2
*DAQ_Move* modules, it could be more convenient to select an area using a rectangular ROI within a 2D viewer. Various
such viewers can be used. For instance, the viewer of a camera (if one think of a camera in a microscope to select an
area to cartography) or even the *DAQ_Scan* 2D viewer. Sometimes it could also be interesting to do linear sections within
a 2D phase space (let's say defined by the ranges of 2 *DAQ_Moves*). This defines complex tabular type scan within a 2D area,
difficult to set manually. :numref:`scan_selector` displays such sections within the DAQ_Scan viewer where a previous
2D scan has been recorded. The user just have to choose the correct *selection* mode in the
*scanner settings*, see :numref:`scan_selector_settings`, and select on which 2D viewer to display the ROI (*From Module* option).



   .. _scan_selector_settings:

.. figure:: /image/DAQ_Scan/scan_selector_settings.png
   :alt: scan_selector

   In the scanner settings, the selection entry gives the choice between *Manual* selection of from *PolyLines*
   (in the case of 1D scans) or *From ROI* in the case of 2D scans.



.. :download:`png <list_modules.png>`


  .. _module_manager:

Module Manager
++++++++++++++

This module is made so that selecting actuators and detectors for a given action is made easy. On top of it, there are
features to test communication and retrieve infos on exported datas (mandatory fro the adaptive scan mode) or positioning.
Internally, it also features a clean
way to synchronize detectors and actuators that should be set together within a single action (such as a scan step).

   .. _module_manager_fig:

.. figure:: /image/DAQ_Scan/list_modules.PNG
   :alt: list_modules

   User interface of the module manager listing detectors and actuators that can be selected for a given action.




.. _H5Browser_module:

H5Browser
---------

The h5 browser is an object that helps browsing of datas and metadatas. It asks you to select a h5 file
and then display a window such as :numref:`figure_h5browser`. Depending the element of the file you are
selecting in the h5 file tree, various metadata can be displayed, such as *scan settings* or
*module settings* at the time of saving. When double clicking on data type entries in the tree, the
data viewer (type :ref:`NDviewer` that can display data dimensionality up to 4)


   .. _figure_h5browser:

.. figure:: /image/Utils/h5browser.PNG
   :alt: h5 browser

   h5 browser to explore saved datas

.. :download:`png <h5browser.png>`


.. _h5saver_module:

H5Saver
-------

This module is a help to save data in a hierachical hdf5 binary file through the **pytables** package. Using the ``H5Saver``
object will make sure you can explore your datas with the H5Browser. The object can be used to: punctually save one set
of data such as with the DAQ_Viewer (see :ref:`daq_viewer_saving_single`), save multiple acquisition such as with the DAQ_Scan
(see :ref:`daq_scan_saving`) or save on the fly with enlargeable arrays such as the :ref:`continuous_saving` mode of the DAQ_Viewer.

   .. _save_settings_fig2:

.. figure:: /image/DAQ_Scan/save_settings.PNG
   :alt: list_modules

   User interface of the H5Saver module

On the possible saving options, you'll find (see :numref:`save_settings_fig2`):


* **Save 2D datas and above**: if not selected, 2D datas (and above) will **not** be saved but only lineouts or
  integrated area (this is only in order to save memory space, but is dangerous as you loose the possibility to get back
  initial raw data. Save raw datas should be unselected in that case)
* **Save raw datas only**: if selected, only data exported form the detector plugins will be saved, not the data
  generated from ROIs or lineouts.
* **Backend**: you can chose among any of the three hdf5 backend (*tables* is recommended and by default)
* **Show File Content?**: if clicked, the :ref:`H5Browser_module` will open to display content of the current hdf5 file
* **Base path**: The folder where all datasets and scans will be saved, for instance: ``C:\Data``
* **Base name**: the name given to the scans you are going to do (default is *Scan*)
* **current Scan**: indexed name from *base name*, for instance: ``Scan000``
* **h5 file**: complete path of the current h5 file, for instance: ``C:\Data\2018\20181226\Dataset_20181226_000\Dataset_20181226_000.h5``
* **Compression options**: by default data are compressed to mid level
  * **compression library**: see *pytables* package or *HDF5* documentation for details
  * **Compression level**: integer between 0 (no compression) and 9 (maximum compression)



.. _preset_manager:

Preset manager
--------------

The *Preset manager* is an object that helps to generate, modify and save preset configurations of :ref:`Dashboard_module`.
A preset is a set of actuators and detectors represented in a tree like structure, see :numref:`preset_fig`, as well as
saving options if the *DAQ_Scan* extension is to be used.


   .. _preset_fig:

.. figure:: /image/DAQ_Scan/preset_fig.png
   :alt: preset_fig

   An example of a preset creation named *preset_adaptive* containing 3 DAQ_Move modules and 3 detector
   modules and just about to select a fourth detector from the list of all available detector plugins.

Each added module load on the fly its settings so that one can set them to our need, for instance COM
port selection, channel activation, exposure time... Every time a preset is created, it is then *loadable*.
The *init?* boolean specifies if DAQ_Scan should try to initialize the hardware while loading the module in the
dashboard.

.. _overshoot_manager:

Overshoot manager
-----------------

The *Overshoot* manager is used to configure **safety actions** (for instance the absolute positioning of one or more
actuators, such as a beam block to stop a laser beam) when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds, see :numref:`overshoot_manager_fig`. It is configurable in the framework of the Dashboard module,
when actuators and detectors have been activated. A file containing its configuration will be saved (with a name derived
from the preset configuration name and will automatically be loaded with its preset if existing on disk)

  .. _overshoot_manager_fig:

.. figure:: /image/DAQ_Scan/overshoot_fig.png
   :alt: overshoot_fig

   An example of an overshoot creation named *overshoot_default* (and corresponding xml file)
   containing one listening detector and 2 actuators to be activated.


.. _roi_manager:

ROI manager
-----------
The *ROI* manager is used to save and load in one click all ROIs or Lineouts defined in the current detector's viewers,
see :numref:`roi_manager_fig`.
The file name will be derived from the preset configuration file, so that at start up, it will automatically be loaded,
and ROIs and Lineouts will be restored.

  .. _roi_manager_fig:

.. figure:: /image/managers/roi_manager.PNG
   :alt: roi_manager_fig

   An example of ROI manager modification named from the preset *preset_adaptive* (and corresponding xml file)
   containing all ROIs and lineouts defined on the detectors's viewers.

DAQ_Measurement
---------------

In construction




Navigator
---------

See :ref:`navigator_paragrah`
