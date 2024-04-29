.. DAQ_Pro_Aquisition documentation master file, created by
   sphinx-quickstart on Mon Apr 16 15:21:28 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyMoDAQ's documentation!
===================================

PyMoDAQ is an open-source software, officially supported by the CNRS, to perform modular data acquisition with Python.
It proposes a set of modules used to interface any kind of experiments. It simplifies the interaction with detector and
actuator hardware to go straight to the data acquisition of interest.


.. raw:: html

   <div style="text-align: center">
      <iframe width="672" height="378" src="https://www.youtube.com/embed/PWuZggs_HwM" title="YouTube video player"
      frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
       allowfullscreen></iframe>
   </div>

French version `here`__

__ https://youtu.be/TrRy6HL3h3c

   .. _training:

Training
********

.. figure:: /image/Flyer_PyMoDAQ.png
   :alt: Flyer_femto

   Training sessions announcement and PyMoDAQ's days

.. note::
   * Third edition of the PyMoDAQ's Days: Lyon 20/22 October 2024. Register on https://pymodaq-jt2022.sciencesconf.org/
   * Training session in Toulouse, France 17/19 June 2024

PyMoDAQ has two purposes:

* First, to provide a complete interface to perform automated measurements or logging data without having to write
  a user/interface for each new experiment.
* Second, to provide various tools (User interfaces, classes dedicated to specific tasks...) to easily build a :ref:`custom_app`

It is divided in two main components as shown on figure :numref:`overview_submodules`

* The :ref:`Dashboard_module` and its control modules: :ref:`DAQ_Move_module` and  :ref:`DAQ_Viewer_module`
* Extensions such as the :ref:`DAQ_Scan_module` or the :ref:`DAQ_Logger_module`


   .. _overview_submodules:

.. figure:: /image/pymodaq_diagram.png
   :alt: overview

   PyMoDAQ's Dashboard and its extensions: DAQ_Scan for automated acquisitions, DAQ_Logger for data logging and many other.


The Control modules are interfacing real instruments using user written plugins. The complete list of available plugins
is maintained on this GitHub `repository`__ and installabled using the :ref:`PluginManager`

__ https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md


Information
***********

GitHub repo: https://github.com/PyMoDAQ

Documentation: http://pymodaq.cnrs.fr/

Scientific `article`__ on Review of Scientific Instruments journal

General public `article`__ on Scientia

List of available `plugins`__

Video tutorials `here`__

Mailing List: https://listes.services.cnrs.fr/wws/info/pymodaq


Credits
*******

Based on the ``pyqtgraph`` library : http://www.pyqtgraph.org by Luke Campagnola.

PyMoDAQ is written by Sébastien Weber: sebastien.weber@cemes.fr under a MIT license.

__ https://doi.org/10.1063/5.0032116

__ https://www.scientia.global/dr-sebastien-weber-pymodaq-navigating-the-future-of-data-acquisition/

__ https://github.com/PyMoDAQ/pymodaq_plugin_manager/

__ https://youtube.com/playlist?list=PLGdoHByMKfIdn-N51goippSSP_9iG4wds


Contribution
************

If you want to contribute see this page: :ref:`contributors`


They use it
***********
See :ref:`feedback`


Citation
********

By using PyMoDAQ, you are being asked to cite the article published in Review of Scientific
Instruments `RSI 92, 045104 (2021)`__ when publishing results obtained with the help of its interface.
In that way, you're also helping in its promotion and amelioration.

__ https://doi.org/10.1063/5.0032116

Changelog
*********

Please see :doc:`the changelog </changelog>`.

.. toctree::
   :numbered:
   :maxdepth: 3
   :caption: Contents:

   features
   whats_new
   user
   developer
   tutorials
   feedback
   glossary
   api/api_doc
   Supported instruments <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>
   PyMoDAQ Femto <https://pymodaq-femto.readthedocs.io/en/latest/>
   PyMoDAQ Plugins DAQmx <https://pymodaq.github.io/pymodaq_plugins_daqmx/>

..   usage/classDiagram


Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
