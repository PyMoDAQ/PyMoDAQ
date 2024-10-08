.. _data_api:

Data Management
***************

.. py:currentmodule:: pymodaq_data.data

.. autosummary::

   DataDim
   DataSource
   DataDistribution
   AxisBase
   Axis
   DataBase
   DataWithAxis
   DataRaw
   DataCalculated
   DataFromPlugins
   DataFromRoi
   DataToExport

Axes
----

.. automodule:: pymodaq_data.data
   :members: AxisBase, Axis

.. _data_objects_api:

DataObjects
-----------

.. automodule:: pymodaq_data.data
   :members: DataBase, DataWithAxis, DataRaw, DataCalculated, DataFromRoi


.. automodule:: pymodaq.utils.data
   :members: DataFromPlugins, DataActuator

Data Characteristics
--------------------

.. automodule:: pymodaq_data.data
   :members: DataDim, DataSource, DataDistribution


.. _datatoexport_api:

Union of Data
-------------

When exporting multiple set of Data objects, one should use a DataToExport

.. automodule:: pymodaq_data.data
   :members: DataToExport