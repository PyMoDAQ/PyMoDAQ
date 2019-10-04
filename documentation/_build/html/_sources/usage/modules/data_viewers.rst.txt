.. _data_viewers:

Data Viewers
============

These modules are to be used to display various type of data and helps you manipulate these using
scaling, ROI, measurements...
They are mostly used within the main modules of PyMoDAQ but can also be used as building
blocks for custom application. In that sense, :ref:`DAQ_Viewer_module` and
:ref:`DAQ_Move_module` can also be used as building blocks to control actuators and display datas in a
custom application.


0D Viewer
---------

   .. _figure_0Dviewer:

.. figure:: /image/Utils/figure_0Dviewer.png
   :alt: figure_0Dviewer

   0D viewer data display

.. :download:`png <figure_0Dviewer.png>`



1D Viewer
---------

   .. _figure_1Dviewer:

.. figure:: /image/Utils/figure_1Dviewer.png
   :alt: figure_1Dviewer

   1D viewer data display

.. :download:`png <figure_1Dviewer.png>`



2D Viewer
---------

   .. _figure_2Dviewer:

.. figure:: /image/Utils/figure_2Dviewer.png
   :alt: figure_2Dviewer

   2D viewer data display

.. :download:`png <figure_2Dviewer.png>`


.. _NDviewer:

ND Viewer
---------
.. |axes| image:: /image/Utils/axis_selection.png
   :width: 20
   :alt: axes

A ND viewer is a display object that can represent 0D, 1D, 2D, 3D or 4D data. It is a combination of 2 Viewers (up:
navigation viewer and bottom: signal viewer, see panels of :numref:`figure_NDviewer`) and use the concept of
*signal* axis and *navigation* axis. Let's say you
want to represent a previously acquired 2D scan where each of the pixels in the scan is actually data from a camera (2D).
It then means that you have 2 navigation axis (the ones of the scan) and two signal axis (the ones of the camera) and
4D data to deal with. The way to plot them is to represent the *scan* on a navigation 2D viewer where each pixel intensity
is the result of the integration of the actual data taken at this pixel (or within a ROI that you can select, see white rectangle
on :numref:`figure_NDviewer` bottom panel). Moving the crosshair on the navigation panel change the display in the signal panel
in order to show the data within the pixel pointed by the crosshair.

   .. _figure_NDviewer:

.. figure:: /image/Utils/figure_NDviewer.png
   :alt: figure_NDviewer

   ND viewer data display

ND viewer is used by the H5Browser to display data saved with PyMoDAQ, a few metadata attributes written in the h5file nodes
(see :ref:`daq_scan_saving`)
tells the NDViewer how to display acquired scans. If, for some reasons, you want to display your 4D data in another way (that is changing
which dimension is navigation and which is signal), you can press the |axes| button on the top viewer and change the navigation
axes on the popup window it opened.
