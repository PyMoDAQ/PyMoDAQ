PyMoDAQ
=======

PyMoDAQ is a free and open-source software, officially supported by the CNRS, to efficiently setup the acquisition
program of your experiment with Python.
It simplifies the interaction with detector and
actuator hardware to go straight to the data acquisition of interest. It provides:

* a graphical interface
* the synchronization of the connected instruments
* data saving
* a modular architecture to easily integrate new instruments in your setup
* ... and many more features!

.. raw:: html

   <div style="text-align: center">
      <iframe width="672" height="378" src="https://www.youtube.com/embed/PWuZggs_HwM" title="YouTube video player"
      frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
       allowfullscreen></iframe>
   </div>

French version `here`_

.. _here: https://youtu.be/TrRy6HL3h3c


.. figure:: /image/JT_Pymodaq_2025.png
   :alt: Pymodaq days

   The 43 people attending the last PyMoDAQ days in Montpellier. This three days workshop allowed multiple discussions
   on realisations, instrumentations, new and future features! See you in october 2026 for the nex PyMoDAQ Days in Orsay



   .. _training:

Next training sessions
----------------------

Training sessions and gathering of the community are organized every year.

.. figure:: /image/flyer_pymodaq.png
   :alt: Flyer_femto

   Training sessions announcement and PyMoDAQ's days

.. note::
   * Training session in Gif sur Yvette, France, 1-5 december 2025, `CNRS Formation Entreprise`_
   * Training session in Gif sur Yvette, France, 3-7 march 2026, `CNRS Formation Entreprise`_
   * Training session in Bordeaux, France, 15-18 June 2026, Action Nationale de Formation CNRS
   * Fifth edition of the PyMoDAQ's Days: Orsay 7-9 October 2026.

.. _CNRS Formation Entreprise: https://cnrsformation.cnrs.fr/liste-stages-mc-PyMoDAq.html

Overview
--------

PyMoDAQ is an advanced user interface to control and synchronize detectors and actuators.
Each of these have their independent interface called respectively :ref:`DAQ Viewer <DAQ_Viewer_module>` and
:ref:`DAQ Move <DAQ_Move_module>` *control modules*.

Detectors and actuators can be wrapped together in a :ref:`Dashboard_module` which implements a particular experimental
setup.
The Dashboard has functionalities to fully configure
all its detectors and actuators and
save their configurations in a :term:`preset` file that will, at startup, load and initialize all modules.

As soon as the Dashboard has been configured, all the :ref:`Dashboard Extensions <extensions>` can be used to perform
advanced and
automated tasks on the detectors and actuators.

* the :ref:`DAQ Scan <DAQ_Scan_module>` is the most common one. It allows to scan one or several actuators while
  acquiring and saving data from the detectors. A very large class or experiments can be performed with this extension.
* the :ref:`DAQ Logger <DAQ_Logger_module>` allows to log all the parameters of an experiment.
* the :ref:`PID extension <PID_module>` allows to lock a parameter of the experiment with a feedback loop on the
  actuators.

... to introduce a few of them!

.. _overview_submodules:

.. figure:: /image/pymodaq_diagram.png
   :alt: overview

   PyMoDAQ's Dashboard and its extensions: DAQ Scan for automated acquisitions, DAQ Logger for data logging and many
   other.

PyMoDAQ is maintained by a growing community of experimental physicists, and already implemented on many experiments.

By contributing to its development, you will learn the cutting edge tools of professional developers and start
experiencing how efficient it is
to code in a collaborative way!

Let’s go for a :ref:`quick_start`!

Contact
-------

You can find video tutorials on the
`YouTube channel <https://youtube.com/playlist?list=PLGdoHByMKfIdn-N51goippSSP_9iG4wds>`_.

Do not hesitate to address your questions to the mailing list
`pymodaq@services.cnrs.fr <mailto:pymodaq@services.cnrs.fr>`_ or
`sebastien.weber@cemes.fr <mailto:sebastien.weber@cemes.fr>`_.

For detailed information about the code and the features of PyMoDAQ, please visit the
`GitHub repository <https://github.com/pymodaq/pymodaq>`_. Do not hesitate to
`submit an issue <https://github.com/pymodaq/pymodaq/issues>`_.

If you would like to get updated with the evolutions of the project, please subscribe to the
`mailing list <https://listes.services.cnrs.fr/wws/info/pymodaq>`_.

.. toctree::
   :caption: Supported instruments

   Supported instruments <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>

.. toctree::
   :numbered:
   :maxdepth: 1
   :caption: Documentation

   quick_start
   user
   tutorials
   lab_story
   data_management
   developer
   glossary
   api/api_doc
   about

.. toctree::
   :caption: Related projects

   PyMoDAQ Femto <https://pymodaq-femto.readthedocs.io/en/latest/>
   PyMoDAQ Plugins DAQmx <https://pymodaq.github.io/pymodaq_plugins_daqmx/>
