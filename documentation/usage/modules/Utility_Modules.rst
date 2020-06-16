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

.. _scanner_paragrah:

Scanner
-------

The *Scanner* module is an object dealing with configuration of scan modes and is mainly used by the DAQ_Scan extension.
It features a graphical interface, see :numref:`scan2D_fig`, allowing the configuration of the scan type and all its
particular settings see below:

Scan1D
++++++

* **Scan type**: set the type of scan, 1D for a scan as a function of only one actuator, 2D for a
scan as a function of two actuators. Other options to come: *batch scan* (list of single scans to perform in a row)
*point scan* (list of positions to scan from), *sequential scan* (sequence of scans)

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

Scan2D
++++++

  .. _scan2D_fig:

.. figure:: /image/managers/scanner_widget.png
   :alt: scanner_fig

   The Scanner user interface set on a *Scan2D* scan type and an *adaptive* scan subtype and its particular settings.



Sequential
++++++++++

Tabular
+++++++


.. _adaptive_scans:

Adaptive
++++++++


All the adaptive features are using the `python-adaptive`__ package (Parallel active learning of
mathematical functions, 10.5281/zenodo.1182437).


__ https://adaptive.readthedocs.io/en/latest/


.. _scan_selector_paragraph:

Scan Selector
+++++++++++++

Scans can be specified manually using the *Scanner Settings* (explained above). However, in the case of a scan using 2
*DAQ_Move* modules, it could be more convenient to select an area using a rectangular ROI within a 2D viewer. Various
such viewers can be used. For instance, the viewer of a camera (if one think of a camera in a microscope to select an
area to cartography) or even the *DAQ_Scan* 2D viewer. Sometimes it could also be interesting to do linear sections within
a 2D phase space (let's say defined by the ranges of 2 *DAQ_Moves*). This defines complex 1D scans within a 2D area,
difficult to set manually. :numref:`scan_selector` displays such sections within the DAQ_Scan viewer where a previous
2D scan has been recorded. The user just have to choose the correct *selection* mode in the
*scanner settings*, see :numref:`scan_selector_settings`, and select on which 2D viewer to display the ROI (*From Module* option).


   .. _scan_selector:

.. figure:: /image/DAQ_Scan/scan_selector.png
   :alt: scan_selector

   An example of 1D complex sections selected within a 2D area



   .. _scan_selector_settings:

.. figure:: /image/DAQ_Scan/scan_selector_settings.png
   :alt: scan_selector

   In the scanner settings, the selection entry gives the choice between *Manual* selection of from *PolyLines*
   (in the case of 1D scans) or *From ROI* in the case of 2D scans.


.. _H5Browser_module:

H5Browser
---------

The h5 browser is an object that helps browsing of datas and metadatas. It asks you to select a h5 file
and then display a window such as :numref:`figure_h5browser`. Depending the element of the file you are
selecting in the h5 file tree, various metadata can be displayed, such as *scan settings* or
*module settings* at the time of saving. When double clicking on data type entries in the tree, the
data viewer (type :ref:`NDviewer` that can display data dimensionality up to 4)


   .. _figure_h5browser:

.. figure:: /image/Utils/h5browser.png
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

See :ref:`H5SaverClassDescr` for a detailled description

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

.. figure:: /image/managers/roi_manager.png
   :alt: roi_manager_fig

   An example of ROI manager modification named from the preset *preset_adaptive* (and corresponding xml file)
   containing all ROIs and lineouts defined on the detectors's viewers.

DAQ_Measurement
---------------

In construction




Navigator
---------

See :ref:`navigator_paragrah`
