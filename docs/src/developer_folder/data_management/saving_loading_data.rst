


Saving and loading data
+++++++++++++++++++++++

Datas saved using PyMoDAQ, either the *DAQ_Scan* or the *DAQ_Viewer* modules or others, use a binary format
known as *hdf5*. This format was originally developed to save big volume of datas from large instruments.
Its structure is hierarchical (a bit as folder trees) and one can add metadata to all entries in the tree.
For instance, the data type, shape but also some more complex info such as all the settings related to a
module or an instrument plugin. This gives a unique file containing both data and metadata.

Python wrappers around the HDF5 library (hdf5 backends) are available, such as h5py or pytables
(default one used by PyMoDAQ). For an even easier use, PyMoDAQ also has a dedicated object
allowing a transparent use of any hdf5 backend: :ref:`H5BackendClassDescr`. It also has an object used
for saving data: :ref:`H5SaverClassDescr` and browsing data: :ref:`H5Browser_module`.

These low level objects allow to interact with PyMoDAQ's data and hdf5 file but because displaying and loading
correctly data need a specific layout and metadata in the hdf5 file, higher level objects should be systematically
used to save and load data. They insure that any data loaded from the hdf5 file will have a correct type:
:ref:`datawithaxes` or :ref:`datatoexport` and that these data objects will be saved with the appropriate layout
and metadata to insure their reconstruction when loading. These objects are defined in the
``pymodaq.utils.h5modules.data_saving`` module. Their specificity is described below. For a more detailed description,
see :ref:`data_saving_loading`


DataSaver/DataLoader
--------------------

Saving and loading data objects is a symmetrical action,  therefore PyMoDAQ defines objects to do both. These objects
all derive from a base class allowing the manipulation of the node (``DataManagement`` object), then the child class should define a *data type* and
will be responsible for saving and loading such data. Data type means here one of the three main type of
PyMoDAQ's data system: :ref:`data_axis`, :ref:`datawithaxes` or :ref:`datatoexport`. These child objects are respectively:
``AxisSaverLoader``, ``DataSaverLoader`` and ``DataToExportSaver``.

They all take as initial parameter a h5saver object (used to initialize a hdf5 file, see :ref:`H5SaverClassDescr`),
then define specific methods to save their data type. Examples:


AxisSaverLoader
###############

First I create a hdf5 file using the H5Saver (here H5SaverLowLevel because I'm not in a Qt event loop)

>>> import numpy as np
>>> from pathlib import Path
>>> from pymodaq.utils.data import Axis
>>> from pymodaq.utils.h5modules.saving import H5SaverLowLevel
>>> h5saver = H5SaverLowLevel()
>>> h5saver.init_file(Path('atemporaryfile.h5'))

Then I create the Axis object and its saver/loader

>>> from pymodaq.utils.h5modules.data_saving import AxisSaverLoader
>>> axis = Axis('myaxis', units='seconds', data=np.array([3,7,11,15]), index=0)
>>> axis_saver = AxisSaverLoader(h5saver)

I save the Axis object in the /RawData node (always created using H5Saver)

>>> axis_saver.add_axis('/RawData', axis)
/RawData/Axis00 (CARRAY) 'myaxis'
                shape := (4,)
                dtype := float64

I can check the content of the file:

>>> for node in h5saver.walk_nodes('/'):
>>>     print(node))
/ (GROUP) 'PyMoDAQ file'
/RawData (GROUP) 'Data from PyMoDAQ modules'
/RawData/Logger (VLARRAY) ''
/RawData/Axis00 (CARRAY) 'myaxis'

And load back from it, an Axis object identical to the initial one (but not the same one)

>>> loaded_axis = axis_saver.load_axis('/RawData/Axis00')
>>> loaded_axis
Axis: <label: myaxis> - <units: seconds> - <index: 0>
>>> loaded_axis == axis
True
>>> loaded_axis is axis
False

DataSaverLoader
###############

The ``DataSaverLoader`` object will behave similarly with DataWithAxes objects, introducing the methods:

* add_data
* load_data

with a slight asymmetry between the two if one want to load background subtracted data previously saved using the
specialized ``BkgSaver``. This guy is identical to the ``DataSaverLoader`` except it considers the DataWithAxes
to be saved as background data type.

Here I create my data and background object:

>>> from pymodaq.utils.data import DataWithAxes, DataSource, DataDim, DataDistribution
>>> data = DataWithAxes('mydata', source=DataSource['raw'], dim=DataDim['Data2D'], \
distribution=DataDistribution['uniform'], data=[np.array([[1,2,3], [4,5,6]])],\
axes=[Axis('vaxis', index=0, data=np.array([-1, 1])),
Axis('haxis', index=1, data=np.array([10, 11, 12]))])
>>> bkg = data.deepcopy()
>>> data
<DataWithAxes, mydata, (|2, 3)>
>>> bkg
<DataWithAxes, mydata, (|2, 3)>

I add a *detector* node in the h5file:

>>> h5saver.add_det_group('/RawData', 'Example')
/RawData/Detector000 (GROUP) 'Example'
  children := []

and save in this node the data:

>>> from pymodaq.utils.h5modules.data_saving import DataSaverLoader
>>> datasaver = DataSaverLoader(h5saver)
>>> datasaver.add_data('/RawData/Detector000', data)

and check the file content:

>>> for node in h5saver.walk_nodes('/'):
>>>     print(node)
/ (GROUP) 'PyMoDAQ file'
/RawData (GROUP) 'Data from PyMoDAQ modules'
/Axis00 (CARRAY) 'myaxis'
/RawData/Logger (VLARRAY) ''
/RawData/Detector000 (GROUP) 'Example'
/RawData/Detector000/Data00 (CARRAY) 'mydata'
/RawData/Detector000/Axis00 (CARRAY) 'vaxis'
/RawData/Detector000/Axis01 (CARRAY) 'haxis'

It saved automatically the Axis objects associated with the data

>>> loaded_data = datasaver.load_data('/RawData/Detector000/Data00')
>>> loaded_data
<DataWithAxes, mydata, (|2, 3)>
>>> loaded_data == data
True
>>> loaded_data is data
False

Now about the background:

>>> from pymodaq.utils.h5modules.data_saving import BkgSaver
>>> bkgsaver = BkgSaver(h5saver)
>>> bkgsaver.add_data('/RawData/Detector000', data, save_axes=False)

no need to save the axes as they are shared between data and its background

>>> for node in h5saver.walk_nodes('/RawData/Detector000'):
>>>     print(node)
/RawData/Detector000 (GROUP) 'Example'
/RawData/Detector000/Data00 (CARRAY) 'mydata'
/RawData/Detector000/Axis00 (CARRAY) 'vaxis'
/RawData/Detector000/Axis01 (CARRAY) 'haxis'
/RawData/Detector000/Bkg00 (CARRAY) 'mydata'

I now have a Bkg data type and can load data with or without bkg included:

>>> loaded_data_bkg = datasaver.load_data('/RawData/Detector000/Data00', with_bkg=True)
>>> loaded_data_bkg
<DataWithAxes, mydata, (|2, 3)>
>>> loaded_data_bkg == loaded_data
False
>>> loaded_data_bkg.data[0]
array([[0, 0, 0],
       [0, 0, 0]])
>>> loaded_data.data[0]
array([[1, 2, 3],
       [4, 5, 6]])


DataToExportSaver
#################

Finally the same apply for ``DataToExport`` containing multiple DataWithAxes. Its associated
``DataToExportSaver`` will save its data into different channel nodes themselves filtered by dimension.
The only difference here, is that it won't be able to load the data back to a dte


Let's say I create a ``DataToExport`` containing 0D, 1D and 2D DataWithAxes (see the tests file):

>>> dte = DataToExport(name='mybigdata', data=[data2D, data0D, data1D, data0Dbis])
>>> from pymodaq.utils.h5modules.data_saving import DataToExportSaver
>>> dte_saver = DataToExportSaver(h5saver)


>>> h5saver.add_det_group('/RawData', 'Example dte')
/RawData/Detector001 (GROUP) 'Example dte'
  children := []

>>> dte_saver.add_data('/RawData/Detector001', dte)


>>> for node in h5saver.walk_nodes('/RawData/Detector001'):
>>>     print(node)
/RawData/Detector001 (GROUP) 'Example dte'
/RawData/Detector001/Data0D (GROUP) ''
/RawData/Detector001/Data1D (GROUP) ''
/RawData/Detector001/Data2D (GROUP) ''
/RawData/Detector001/Data0D/CH00 (GROUP) 'mydata0D'
/RawData/Detector001/Data0D/CH01 (GROUP) 'mydata0Dbis'
/RawData/Detector001/Data1D/CH00 (GROUP) 'mydata1D'
/RawData/Detector001/Data2D/CH00 (GROUP) 'mydata2D'
/RawData/Detector001/Data2D/CH00/Data00 (CARRAY) 'mydata2D'
/RawData/Detector001/Data2D/CH00/Data01 (CARRAY) 'mydata2D'
/RawData/Detector001/Data2D/CH00/Axis00 (CARRAY) 'myaxis0'
/RawData/Detector001/Data2D/CH00/Axis01 (CARRAY) 'myaxis1'
/RawData/Detector001/Data1D/CH00/Data00 (CARRAY) 'mydata1D'
/RawData/Detector001/Data1D/CH00/Data01 (CARRAY) 'mydata1D'
/RawData/Detector001/Data1D/CH00/Axis00 (CARRAY) 'myaxis0'
/RawData/Detector001/Data0D/CH00/Data00 (CARRAY) 'mydata0D'
/RawData/Detector001/Data0D/CH00/Data01 (CARRAY) 'mydata0D'
/RawData/Detector001/Data0D/CH01/Data00 (CARRAY) 'mydata0Dbis'
/RawData/Detector001/Data0D/CH01/Data01 (CARRAY) 'mydata0Dbis'

Here a bunch of nodes has been created to store all the data present in the dte object.


DataLoader
##########

If one want to load several nodes at ones or include the navigation axes saved at the root of the nodes, one should
use the ``DataLoader`` that has methods to load one DataWithAxes (including eventual navigation axes) or a bunch of it
into a ``DataToExport``:


* load_data -> ``DataWithAxes``
* load_all -> ``DataToExport``

Special DataSaver
#################

Some more dedicated objects are derived from the objects above. They allow to add Extended arrays
(arrays that will be populated after creation, for instance for a scan) and Enlargeable arrays (whose final length
is not known at the moment of creation, for instance when logging or continuously saving)
see :ref:`specific_data_saver`.