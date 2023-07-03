
.. _H5Browser_module:

H5Browser
=========

The h5 browser is an object that helps browsing of datas and metadatas. It asks you to select a h5 file
and then display a window such as :numref:`figure_h5browser`. Depending the element of the file you are
selecting in the h5 file tree, various metadata can be displayed, such as *scan settings* or
*module settings* at the time of saving. When double clicking on data type entries in the tree, the
data viewer (type :ref:`NDviewer` that can display data dimensionality up to 4) will display the selected data
node
.

   .. _figure_h5browser:

.. figure:: /image/Utils/h5browser.PNG
   :alt: h5 browser

   h5 browser to explore saved datas

.. :download:`png <h5browser.png>`


Some options are available when right clicking on a node, see :numref:`figure_h5browser_options`.



   .. _figure_h5browser_options:

.. figure:: /image/Utils/h5browser_right_click.PNG
   :alt: h5 browser

   h5 browser options

* Export as: allow exporting of the data in the selected node to another known file format
* Add Comment: add a comment into the metadata of the node
* Plot Node: plot data (equivalent as double clicking)
* Plot Nodes: plot data hanging from the same channel
* Plot Node with Bkg: plot data with subtracted background (if present)
* Plot Nodes with Bkg: plot data hanging from the same channel with subtracted background (if present)
