.. _data_api:

Data Management
***************

.. py:currentmodule:: pymodaq.utils.data

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

.. automodule:: pymodaq.utils.data
   :members: AxisBase, Axis

.. _data_objects_api:

DataObjects
-----------

.. automodule:: pymodaq.utils.data
   :members: DataBase, DataWithAxis, DataRaw, DataCalculated, DataFromPlugins, DataFromRoi


Data Characteristics
--------------------

.. automodule:: pymodaq.utils.data
   :members: DataDim, DataSource, DataDistribution


.. _datatoexport_api:

Union of Data
-------------

When exporting multiple set of Data objects, one should use a DataToExport

.. automodule:: pymodaq.utils.data
   :members: DataToExport