
.. _H5Browser_module:

H5Browser
=========

Exploring data
++++++++++++++

The h5 browser is an object that helps browsing of data and metadata. It asks you to select a h5 file
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

Associating H5Browser with .h5 files
+++++++++++++++++++++++++++++++++++++

By default, the H5Browser always asks the user to select a file. One can instead open a specified .h5 file directly,
using the --input optional command line argument as follows:

``h5browser --input my_h5_file.h5``.

One can also associate H5Browser to all .h5 file so that it directly opens a file when double clicking on it. Here is
how to do it on Windows. Let us assume that you have a conda environment named *my_env*, in which PyMoDAQ is installed.

In Windows, the path to your conda executable will be something like:

``C:\Miniconda3\condabin\conda.bat``


Now that you have written down this path, open your favorite text editing tool (e.g. notepad) and create a file
called *H5Opener.bat* (for instance) with the following contents:

  .. code-block:: python

    @ECHO OFF
    call C:\Miniconda3\condabin\conda.bat activate my_env
    h5browser --input %1

.. note::
   The precise path of your environment may be different from the one we wrote just above. Check
   your conda installation to verify this: `conda info` and `conda env list`

After creating the file, simply right click on any .h5 file, choose **Open with**, *Try an app on this PC*, you should see a list of programs, at the bottom
you have to tick *Always use this app to open .h5 files* and then click *Look for another app on this PC*. You can browse to the location
of *H5Opener.bat* and you are done. Double clicking any .h5 file will now open the H5Browser directly loading the selected file.
