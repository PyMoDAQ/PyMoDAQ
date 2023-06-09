

Data Management
===============
Data are at the center of the PyMoDAQ ecosystem. From their acquisition up to
their saving and plotting, you'll be confronted with them. It is therefore of
paramount importance that data objects be well understood and be used
transparently by all of PyMoDAQ's modules.


What is PyMoDAQ's Data?
+++++++++++++++++++++++

Data in PyMoDAQ are numbers with many characteristics:

* a type: float, int, ...
* a dimensionality: Data0D, Data1D, Data2D and will discuss about DataND
* units
* axes

Because of this variety, PyMoDAQ introduce a set of objects including metadata (for instance the time of acquisition)
and various methods and properties to manipulate those (getting name, slicing, concatenating...). The most basic object
is `DataBase`. It stores homogeneous data (data of same type) having the same shape as a list of numpy arrays.

Numpy is fundamental in python and it was obvious to choose that. However, instruments can acquire data having the same
type and shape but from different channels. It then makes sense to have a list of numpy arrays.


DataBase
--------

`DataBase`, see :ref:`data_objects`, is the most basic object to store data. It takes as argument a name,
a :term:`DataSource`, a :term:`DataDim`, a :term:`DataDistribution`, the actual data as a list of numpy arrays (even for scalars), labels (a name for each element
in the list), eventually an origin (a string from which module it originates) and optional named arguments.

When instantiated, some checks are performed:

* checking the homogeneity of the data
* the consistency of the dimensionality and the shape of the numpy arrays

Useful properties can then be used to check and manipulate the data.
For instance one can check the `length` of the object (number of numpy arrays in the list), the size (number of elements
in the numpy arrays), the shape (shape of the numpy arrays). One can also make mathematical operations between data
objects (sum, substraction, averaging) or appending numpy arrays (of same type and shape) to the data object and
iterating over the numpy arrays with the standard `for` loop.
For a full description see :ref:`data_objects`.

One course for data that are not scalar, a very important information is the axis associated with the data (one axis
for waveforms, two for 2D data or more fro hyperspectral data). PyMoDAQ therefore introduces `Axis` and `DataWithAxis`
objects.

Axis
----



DataWithAxis
------------


DataToExport
------------
DataBase
DataWithAxis
DataToExport


How to save such data?
++++++++++++++++++++++
hjdhgj


How to load data?
+++++++++++++++++


