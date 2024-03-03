.. _ploting_data:

Plotting Data
+++++++++++++

As we've seen above, data in PyMoDAQ is featured with a lot of metadata, allowing its proper
description and enabling seamlessly saving/loading to hdf5 files. But what about representation?
Analysis? Exploration?

With Python you usually do this by writing a script and manipulate and plot your data using your
favorite backend (matplotlib, plotly, qt, tkinter, ...) However because PyMoDAQ is highly graphical
you won't need that. PyMoDAQ is featured with various :ref:`data_viewers` allowing you to plot any
kind of data. You'll see below some nice examples of how to plot your PyMoDAQ's data using the builtin
data viewers.

Plotting scalars
----------------

Scalars or `Data0D`