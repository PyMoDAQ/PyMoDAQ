.. _datamixer_extension:

DataMixer
=========

.. figure:: datamixer_data/datamixer_logo.png
   :alt: logo
   :width: 80%

   The DataMixer extension allowing to mix/process unrelated data to be used as a brand new source of data!


Introduction
++++++++++++

When dealing with PyMoDAQ you may be frustrated because you cannot easily customize the behaviour of the modules. In
particular the DAQ_Viewer module grab raw data and except by the use of regions of interest you cannot really
post-process those data. In fact there are solutions but they are quite complex especially if one want to do regular
and often varying post-processing. These solutions are:

* to create another plugin inheriting from the standard one and doing the post-processing in the reimplemented
  `grab_data` method. Here you can process the data from only one detector module and you don't have access to
  the regions of interest
* create an extension to perform the post-processing by capturing all the exported data from the Dashboard. But then
  you cannot use that to plot live data during a scan.

Those solutions both have limitations, those are what the DataMixer will solve!

The DataMixer allows you to:

* do operations between unrelated data (that is from various detectors), either raw or from ROI or more generally
  post-process the generated data from the DashBoard
* emulates a virtual DAQ_Viewer module that seems to grab data out of the DataMixer, hence allowing those processed
  data to be used in any DashBoard extension, for instance the DAQ_Scan!


Usage
+++++


The models or how to tailor the post-processing
-----------------------------------------------

Models are classes allowing to customize the post-processing. They have been introduced quite a long time ago by the
:ref:`PID_module` and are heavily used by the optimizing :ref:`Bayesian <bayesian_extension>` and
:ref:`Adaptive <adaptive_extension>` modules. They are therefore also used in the DataMixer to perform custom tasks.
But they are still python classes one has to write for each postprocessing one want to try. They are therefore okay if
you're going to often use them or if they are general enough to be used in various situations. The tow models shipped
with the extension are of the last kind. The first is the Gaussian fit model allowing to fit 1D data by Gaussians, see
figure :numref:`datamixer_gaussian_fit`. The second allows you to define in a text box the mathematical expressions you
want to perform between you raw data, see :ref:`equation_model`.


.. _equation_model:

The Equation Model
------------------


.. _equation_model_fig:

.. figure:: datamixer_data/equation_model_gui.png
   :alt: equation model gui
   :width: 100%

   The DataMixer GUI with the initialized Equation model!

Figure :numref:`equation_model_fig` shows the DataMixer GUI after the equation model has been initialized. The left
panel is for the settings while the right one displays processed data. You first have to select your model (its specific
settings will be displayed when chosen) and initialize it. Then you can select the detectors (from the DashBoard) whose
data you want to use in the post-processing. All the available DataWithAxes (dwa)  generated PyMoDAQ
data will be displayed in the settings (either raw or from ROI) once you press the ``Get Data`` button.
You can then copy/paste them in the
``Edit Formula`` area. You'll have to write them between curly brackets for the parser to interpret them as the full dwa
object. Dwa can handle operations between them such as regular addition, substraction... but are also compatible with
most of the numpy functions such as ``np.sum``, ``np.abs``, ... If you find an error while trying to use a numpy
function, it's probably because it is not yet possible to use it, open an issue and it will be done! Finally each
line/operation in the edit area, will be interpreted as a Dwa and every time you press the snap button the resulting dwa
will be plotted in dedicated viewer panel (they are three of them in the case of figure :numref:`equation_model_fig`.


The Gaussian fit model
----------------------

The Gaussian fit model is a bit more simple, it will try to fit every 1D data you selected... It's more of an example
of a custom model than a versatile one...





Emulating a virtual detector
++++++++++++++++++++++++++++

Alright you performed the super, crazy, Nobel prize winning post-processing, so what? The next step is to create a
virtual detector in the Dashboard generating data from the DataMixer extension. Because those post-processed data now
will seem to come from the DashBoard, all the other extensions will be able to use it. With the DAQ_scan you could
now look at live post-process data while scanning!!! For this to happen just press the |plus| button and a new
DAQ_Viewer will appear in the Dashboard!!

.. |plus| image:: datamixer_data/plus.png