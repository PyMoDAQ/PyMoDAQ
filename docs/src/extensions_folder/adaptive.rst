.. _adaptive_extension:

Adaptive Scanning
=================

First of all, this work is heavily supported by the work of Bas Nijholt and co-workers
through their python package:
`python-adaptive <https://github.com/python-adaptive/adaptive>`__

Introduction
++++++++++++

*Adaptive is an open-source Python library that*
*streamlines adaptive parallel function evaluations. Rather than calculating all points on a dense grid, it*
*intelligently selects the "best" points in the parameter space based on your provided function and bounds.*
*With minimal code, you can perform evaluations on a computing cluster, display live plots, and optimize the adaptive*
*sampling algorithm.*

This, above, is a citation from the authors of the python-adaptive package. It is meant firstly to evaluate
complex functions in a "intelligent" subset of the parameter space. In the PyMoDAQ framework, we often
register data as a function of one or a few varying parameters. The :ref:`DAQ_Scan_module` allows this on a
predetermined grid that could be uniform or more complex but always predetermined. This means that we have to wait for
the end of the scan to know if the settings of the scan implied a good sampling of our parameter space to reveal regions
where our data variation is of interest. Adaptive scanning now allows a sampling being determined through learning of
previously probed parameters. The algorithm will sample finely the parameter space where the data vary quickly as a
function of the parameters, while it will only sample roughly where the signal is constant or just null.

Of course there are some limitations:

* The first one is to decide what *observable* will be used by the algorithm to
  perform the sampling learning. It has to be a 0D pymodaq data, either raw from a detector, calculated though a ROI or
  a more complex one using the :ref:`datamixer_extension`.
* The second is related to the fact that the parameter space will be probed kind of randomly where from
  one step to another, a scanned parameter value can vary a lot. This could be a problem if:

  *  the actuator driving this parameter has some kind of hysteresis or backlash
  *  the parameter variation is very slow. The gained time compared to a dense uniform sampling will not be much.

* Because the algorithm learns from variation of measurements, the results of a measurement of the *observable* should
  not be too noisy.