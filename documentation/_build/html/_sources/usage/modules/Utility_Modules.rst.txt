Utility Modules
===============

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Introduction
------------

Utility modules are used within each main modules of PyMoDAQ but can also be used as building
blocks for custom application. In that sense, all :ref:`data_viewers` and even :ref:`DAQ_Viewer_module` and
:ref:`DAQ_Move_module` can be used as building blocks to control actuators and display datas in a
custom application.





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


.. _preset_manager:

Preset manager
--------------

The *Preset manager* is an object that helps generate, modify and save preset modes of :ref:`DAQ_Scan_module`.
A preset is a set of
actuators and detectors represented in a tree like structure, see :numref:`preset_fig`

   .. _preset_fig:

.. figure:: /image/DAQ_Scan/preset_fig.png
   :alt: preset_fig

   An example of a preset creation named *preset_default* containing one DAQ_Move module and one detector
   module and just about to select a second detector from the list of all available detector plugins.

Each added module load on the fly its settings so that one can set them to our need, for instance COM
port selection, channel activation, exposure time... Every time a preset is created, it is them *loadable*.
The *init?* boolean specifies if DAQ_Scan should try to initialize the hardware while charging the modules.

.. _overshoot_manager:

Overshoot manager
-----------------

The *Overshoot* manager is used to configure actions (for instance the absolute positionning of one or more
actuators, such as a beam block to stop a laser eam) when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds. It is valid in the framework of the DAQ_Scan module,
when actuators and detectors have been activated.

.. figure:: /image/DAQ_Scan/overshoot_fig.png
   :alt: overshoot_fig

   An example of an overshoot creation named *overshoot_default* (and corresponding xml file)
   containing one listening detector and 2 actuators to be activated.

DAQ_Measurement
---------------

