Hdf5 module and classes
=======================

.. currentmodule:: pymodaq.utils.h5modules.backends

.. _H5BackendClassDescr:

Hdf5 backends
-------------

The H5Backend is a wrapper around three hdf5 python packages: pytables, h5py and h5pyd. It allows seamless integration
of any of these with PyMoDAQ features.

.. autoclass:: H5Backend
   :members:



.. _H5SaverClassDescr:

Low Level saving
----------------

``H5SaverBase`` and ``H5Saver`` classes are a help to save data in a hierachical hdf5 binary file through the H5Backend
object and allowing integration in the PyMoDAQ Framework. These objects allows the creation of a file, of the various
nodes necessary to save PyMoDAQ's data. The saving functionalities are divided in two objects: `H5SaverBase` and ``H5Saver``. `H5SaverBase` contains everything
needed for saving, while ``H5Saver``, inheriting `H5SaverBase`, add Qt functionality such as emitted signals. However,
these are not specific of PyMoDAQ's data types. To save and load data, one should use higher level objects, see
:ref:`data_saving_loading`.

.. currentmodule:: pymodaq.utils.h5modules.saving

.. automodule:: pymodaq.utils.h5modules.saving
   :members: H5SaverBase, H5Saver


They both inherits from the ``ParameterManager`` MixIn class that deals with Parameter and ParameterTree,
see :numref:`saving_settings_fig`.


.. _data_saving_loading:

High Level saving/loading
-------------------------

Each PyMoDAQ's data type: ``Axis``, ``DataWithAxes``, ``DataToExport`` (see :ref:`data_objects`) is associated
with its saver/loader
counterpart. These objects ensures that all metadata necessary for an exact regeneration of the data is being saved at
the correct location in the hdf5 file hierarchy. The ``AxisSaverLoader``, ``DataSaverLoader``, ``DataToExportSaver``
all derive from an abstract class: ``DataManagement`` allowing the manipulation of the nodes and making sure the data type
is defined.

Base data class saver/loader
****************************

.. currentmodule:: pymodaq.utils.h5modules.data_saving

.. automodule:: pymodaq.utils.h5modules.data_saving
   :members: DataManagement, AxisSaverLoader, DataSaverLoader, DataToExportSaver


.. _specific_data_saver:

Specific data class saver/loader
********************************

Some more dedicated objects are derived from the objects above. They allow to add background data, Extended arrays
(arrays that will be populated after creation, for instance for a scan) and Enlargeable arrays (whose final length
is not known at the moment of creation, for instance when logging or continuously saving)


.. currentmodule:: pymodaq.utils.h5modules.data_saving

.. automodule:: pymodaq.utils.h5modules.data_saving
   :members: BkgSaver, DataExtendedSaver, DataEnlargeableSaver, DataToExportEnlargeableSaver, DataToExportTimedSaver, DataToExportExtendedSaver


Specialized loading
-------------------

Data saved from a ``DAQ_Scan`` will naturally include navigation axes shared between many different DataWithAxes
(as many as detectors/channels/ROIs). They are therefore saved at the root of the scan node and cannot be retrieved
using the standard data loader. Hence this ``DataLoader`` object.

.. autoclass:: DataLoader
   :members:

Browsing Data
-------------

Using the `H5Backend` it is possible to write scripts to easily access a hdf5 file content. However, PyMoDAQ includes
a dedicated hdf5 viewer understanding dedicated metadata and therefore displaying nicely the content of the file,
see :ref:`H5Browser_module`. Two objects can be used to browse data: `H5BrowserUtil` and `H5Browser`. `H5BrowserUtil`
gives you methods to quickly (in a script) get info and data from your file while the `H5Browser` adds a UI to interact with the hdf5
file.

.. currentmodule:: pymodaq.utils.h5modules.browsing

.. automodule:: pymodaq.utils.h5modules.browsing
   :members: H5BrowserUtil, H5Browser


.. _module_savers_api:

Module savers
-------------

.. currentmodule:: pymodaq.utils.h5modules.module_saving

.. automodule:: pymodaq.utils.h5modules.module_saving
   :members: ModuleSaver, DetectorSaver, DetectorEnlargeableSaver, DetectorExtendedSaver, ActuatorSaver, ScanSaver, LoggerSaver