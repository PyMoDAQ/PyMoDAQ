.. _data_api:

Data Management
***************

.. py:currentmodule:: pymodaq_data.data

.. autosummary::

   DataDim
   DataSource
   DataDistribution
   Axis
   DataBase
   DataWithAxes
   DataRaw
   DataCalculated
   DataFromRoi
   DataToExport
   pymodaq.utils.data.DataFromPlugins
   pymodaq.utils.data.DataActuator

Axes
----

.. automodule:: pymodaq_data.data
   :no-index:
   :members: Axis

.. _data_objects_api:

DataObjects
-----------

.. automodule:: pymodaq_data.data
   :no-index:
   :members: DataBase, DataWithAxes, DataRaw, DataCalculated, DataFromRoi


.. automodule:: pymodaq.utils.data
   :members: DataFromPlugins, DataActuator

Data Characteristics
--------------------

.. automodule:: pymodaq_data.data
   :no-index:
   :members: DataDim, DataSource, DataDistribution


.. _datatoexport_api:

Union of Data
-------------

When exporting multiple set of Data objects, one should use a DataToExport

.. automodule:: pymodaq_data.data
   :no-index:
   :members: DataToExport