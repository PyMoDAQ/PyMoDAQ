.. _bayesian_extension:

Bayesian Optimisation
=====================

First of all, this work is heavily supported by the work of Fernando Nogueira through its python package:
`bayesian-optimization <https://github.com/bayesian-optimization/BayesianOptimization>`__ and the underlying use
of Gaussian Process regression from `scikit-learn <https://scikit-learn.org/stable/modules/gaussian_process.html>`__.

Introduction
++++++++++++

You'll find below, a very short introduction, for a more detailed one, you can also read
`this article <https://medium.com/@okanyenigun/step-by-step-guide-to-bayesian-optimization-a-python-based-approach-3558985c6818>`__
from Okan Yenigun from which this introduction is derived.

Bayesian optimization is a technique used for the global optimization (finding an optimum) of black-box functions. Black box
functions are mathematical functions whose internal details are unknown. However given a set of input parameters,
one can evaluate the possibly noisy output of the function. In the PyMoDAQ ecosystem, such a black box would
often be the physical system of study and the physical observation we want to optimize given a certain number
of parameters. Two approaches are possible: do a grid search or random search using the ``DAQ_Scan`` extension that can
prove inefficient (you can miss the right points) and very lengthy in time or
do a more intelligent phase space search by building a probabilistic surrogate model of our black box by using the
history of tested parameters.

Gaussian Processes:
-------------------
The surrogate model we use here is called Gaussian Process, GP. A Gaussian process defines a distribution
of functions potentially fitting the data. This finite set of function values follows a multivariate Gaussian
distribution. In the context of Bayesian optimization, a GP is used to model the unknown objective function,
and it provides a posterior distribution over the function values given the observed data.

.. figure:: bayesian_data/GP.png
   :alt: Gaussian Process

   Illustration of Gaussian process regression in one dimension. Gaussian processes are specified by an
   estimation function and the uncertainty function evolving constantly as more and more *points* are being tested.
   `Source <https://www.researchgate.net/publication/327613136_Bayesian_optimization_for_likelihood-free_cosmological_inference>`__

From this distribution, a mean value (`µ`) and standard deviation (`std`) of the function distribution is computed. These are then used
to model our black box system. To go one step beyond, the algorithm should predict which parameters should be probed
next to optimize the mean and std. For this we'll construct a simple function based on the probability output of the GP:
the acquisition function.

.. note::
  GPs are themselves based on various kernels (or covariance matrix or *function generator*). Which kernel to use
  may depend on your particular problem, even if the standard ones (as provided in PyMoDAQ should just work fine).
  If you want to know more on this just browse  `here <https://www.cs.toronto.edu/~duvenaud/cookbook/>`__

Acquisition function:
---------------------


Usage
+++++

Models
------

Optimisation signal
___________________

Settings
--------
bounds
ini random

Plots
-----


