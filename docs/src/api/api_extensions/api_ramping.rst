.. _ramping_api:

The Ramping Extension
=====================

Summary of the main classes of the :ref:`Ramping extension <ramping_extension>`.

The Extension
-------------

.. currentmodule:: pymodaq.extensions.ramping.ramping

.. autosummary::

   RampExtension
   RampingWorker

.. autoclass:: RampExtension
   :members:

.. autoclass:: RampingWorker
   :members:


Ramp and data saving
--------------------

.. autoclass:: pymodaq.extensions.ramping.utilities.ramp_generator.RampGenerator
   :members:

.. autoclass:: pymodaq.extensions.ramping.utilities.module_saver.RampSaver
   :members:


Histogram
---------

.. currentmodule:: pymodaq.extensions.ramping.utilities.histograming

.. autosummary::

   H5Histogramming
   HistogramProcessor
   InfoForHistogram

.. autoclass:: H5Histogramming
   :members:

.. autoclass:: HistogramProcessor
   :members:

.. autoclass:: InfoForHistogram
   :members:
