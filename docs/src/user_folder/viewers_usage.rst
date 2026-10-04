.. _viewers_usage:

Using the data viewers
======================

Each :ref:`DAQ_Viewer <DAQ_Viewer_module>` displays its data in one or several data viewers, depending on the
dimensionality of the data sent by its instrument plugin: *Viewer0D* for scalars, *Viewer1D* for waveforms,
*Viewer2D* for images and *ViewerND* for anything else. The same viewers are used everywhere in PyMoDAQ (scans,
H5Browser, extensions...).

This page explains how to use them from their toolbar: the crosshair, the Regions Of Interest (ROIs) that produce
new data from the displayed ones, and the *ROI select*, a selection sent back to the instrument plugin.
For the programmatic use of the viewers (plotting your own data objects) and the ViewerND, see
:ref:`data_viewers`.

.. note::

   The default state (checked or not) of most toolbar buttons can be set in the *viewer* section of the *gui*
   preferences, see :ref:`configfile`. For instance ``ROIselect = true`` in ``[viewer.viewer2D]`` makes the
   ROI select visible when a Viewer2D is created.


Toolbars
--------

Viewer1D
++++++++

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Button
     - Action
   * - |roi1D|
     - Show the ROI manager to define regions of interest on the waveforms, see :ref:`viewers_rois`
   * - |crosshair1D|
     - Show the crosshair, see :ref:`viewers_crosshair`
   * - |aspect1D|
     - Fix the horizontal/vertical aspect ratio
   * - |dot1D|
     - Show the data as dots only (scatter)
   * - |xy1D|
     - With two waveforms, plot one as a function of the other (XY mode)
   * - |overlay1D|
     - Keep an overlay (dashed line) of the current data
   * - |sort1D|
     - Sort the data by ascending axis values (useful for non monotonous axes)
   * - |errors1D|
     - Show the errors (if any) as an area around the curves
   * - |roiselect1D|
     - Show the ROI select, see :ref:`viewers_roi_select`

Viewer2D
++++++++

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Button
     - Action
   * - |rgb2D|
     - Show/hide the red, green or blue channel (one per array of the data)
   * - |autoscale2D|
     - Autoscale the color levels (optionally symmetric around zero)
   * - |histogram2D|
     - Show the histogram panel to set the color levels manually
   * - |roi2D|
     - Show the ROI manager and the lineout panels, see :ref:`viewers_rois`
   * - |isocurve2D|
     - Show an isocurve, whose level is set from the histogram
   * - |aspect2D|
     - Fix the aspect ratio to one
   * - |crosshair2D|
     - Show the crosshair and its lineouts, see :ref:`viewers_crosshair`
   * - |roiselect2D|
     - Show the ROI select, see :ref:`viewers_roi_select`
   * - |orientation2D|
     - Flip the image up/down or left/right, or rotate it
   * - |legend2D|
     - Show/hide the legend

When the ROI manager or the crosshair is shown, an extra button links the zoom of the lineout panels to the one of
the image.

Images are displayed in the units of their axes: the coordinates read on the viewer (mouse position, crosshair,
ROIs, ROI select) are given in these units, or in pixels when the data has no axes.


.. _viewers_crosshair:

Crosshair
---------

The crosshair is a vertical line (Viewer1D) or a pair of lines (Viewer2D) that you can drag, or move with a double
click on the plot. The values of the data at its position are printed in the toolbar. In a Viewer2D, it also
displays the horizontal and vertical lineouts of the image along its lines, and the value at its position, see
:numref:`saturated_fig`.

Its position is sent to the instrument plugin each time it is moved, so that a plugin can use it (for instance to
point a scanner to the selected position), see :ref:`plugin_roi_select`.


.. _viewers_rois:

Regions of interest
-------------------

The ROI manager (|roi1D| / |roi2D| button) is a panel listing the ROIs of the viewer. Use its *Add* button to create
a new ROI:

* in a Viewer1D, a ROI is a region along the axis, delimited by two draggable lines;
* in a Viewer2D, you can choose between a rectangular (*RectROI*), elliptical (*EllipseROI*) or circular
  (*CircularROI*) ROI, that you can move, resize and, for the rectangular one, rotate.

Each ROI has its own settings, also editable from the panel:

* *Use channel*: the data channel(s) (traces of a Viewer1D, red/green/blue arrays of a Viewer2D) the ROI applies to;
* *Math type*: the operation applied on the data within the ROI: *mean*, *sum*, *std*, *max*, *min*, or the position
  of a feature (*argmax*, *argmin*, *argmean*, *argstd*);
* its position and size, its color, and in 2D its type and angle.

Each ROI produces new data, computed every time the viewer receives data:

* in a Viewer1D, a scalar per ROI and channel, plotted below the waveforms;
* in a Viewer2D, the horizontal and vertical lineouts (*Hlineout*, *Vlineout*, the math operation applied along one
  direction of the ROI) and a scalar (*Integrated*, applied along both directions), plotted in the lineout panels.

.. figure:: /data_management/plotting_data/viewer1D_with_roi_crosshair_dot.png
   :alt: Viewer1D with a ROI and the crosshair

   A Viewer1D with a ROI (its mean value is plotted on the bottom panel) and the crosshair.

These data are sent along with the raw data of the DAQ_Viewer: they can be used by the extensions (DAQ_Scan,
DAQ_Logger...) as any other data, and are saved in the h5 files unless the *Save raw data only* option is checked
(see :ref:`h5saver_module`).

The *save* and *load* buttons of the panel store or restore the ROIs of a viewer as an xml file (by default in the
*settings* folder of the user *.pymodaq* folder). To save and restore the ROIs of all the detectors of an experiment
at once, use the Dashboard :ref:`roi_manager`.


.. _viewers_roi_select:

ROI select
----------

The ROI select (|roiselect1D| / |roiselect2D| button) is a single extra selection, independent of the ROI manager:

* in a Viewer1D, a region delimited by two draggable lines;
* in a Viewer2D, a rectangle, that you can move and resize (it can't be rotated). When shown, it covers the central
  part of the view.

It doesn't produce any data by itself. Instead, each time you release it after moving or resizing it, its position
and size are sent to the instrument plugin of the DAQ_Viewer (in the units of the viewer axes). What happens then
depends on the plugin. Typical uses are:

* cropping the data emitted by the plugin to the selected area;
* setting a hardware ROI on a camera, to read only the selected pixels and increase the frame rate.

If a plugin doesn't use it, moving the ROI select has no effect. To use it in your own plugin, see
:ref:`plugin_roi_select`.

.. figure:: /data_management/plotting_data/viewer2D_roi_select.png
   :alt: ROI select button

   The ROI select button of the Viewer2D toolbar.


.. |roi1D| image:: /data_management/plotting_data/viewer1D_roi.png
.. |crosshair1D| image:: /data_management/plotting_data/viewer1D_crosshair.png
.. |aspect1D| image:: /data_management/plotting_data/viewer1D_zoom.png
.. |dot1D| image:: /data_management/plotting_data/viewer1D_dot.png
.. |xy1D| image:: /data_management/plotting_data/viewer1D_xy.png
.. |overlay1D| image:: /data_management/plotting_data/viewer1D_overlay.png
.. |sort1D| image:: /data_management/plotting_data/viewer1D_sort.png
.. |errors1D| image:: /data_management/plotting_data/viewer1D_errors.png
.. |roiselect1D| image:: /data_management/plotting_data/viewer1D_roi_select.png
.. |rgb2D| image:: /data_management/plotting_data/viewer2D_rgb.png
.. |autoscale2D| image:: /data_management/plotting_data/viewer2D_autoscale.png
.. |histogram2D| image:: /data_management/plotting_data/viewer2D_histogram.png
.. |roi2D| image:: /data_management/plotting_data/viewer2D_roi.png
.. |isocurve2D| image:: /data_management/plotting_data/viewer2D_isocurve.png
.. |aspect2D| image:: /data_management/plotting_data/viewer2D_aspect.png
.. |crosshair2D| image:: /data_management/plotting_data/viewer2D_crosshair.png
.. |roiselect2D| image:: /data_management/plotting_data/viewer2D_roi_select.png
.. |orientation2D| image:: /data_management/plotting_data/viewer2D_orientation.png
.. |legend2D| image:: /data_management/plotting_data/viewer2D_legend.png
