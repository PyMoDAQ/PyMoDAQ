.. _bayesian_api:

The Bayesian Extension and utilities
====================================

.. py:currentmodule:: pymodaq.extensions

Summary of the main classes for the Bayesian Optimization extension

.. autosummary::

   BayesianOptimization
   optimizers_base.models.OptimizerModelGeneric
   optimizers_base.models.OptimizerModelDefault


The Extension module
--------------------

.. autoclass:: BayesianOptimization
   :members:

The Base Models
---------------

The models are shared by all the optimizer extensions (see :mod:`pymodaq.extensions.optimizers_base`).

.. py:currentmodule:: pymodaq.extensions.optimizers_base.models

.. autoclass:: OptimizerModelGeneric
   :members:

.. autoclass:: OptimizerModelDefault
   :members:

