.. DAQ_Pro_Aquisition documentation master file, created by
   sphinx-quickstart on Mon Apr 16 15:21:28 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyMoDAQ's documentation!
===================================

..
   Announcement: Training session in Toulouse, France 12/13/14 Octobre 2020:

      .. _flyer:

   .. figure:: /image/Flyer_PyMoDAQ.png
      :alt: Flyer_femto

      Training session announcement

PyMoDAQ, Modular Data Acquisition with Python, is a set of **python** modules used to interface any kind of experiments.
It simplifies the interaction with detector and actuator hardware to go straight to the data acquisition of interest.

It has two purposes:

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

__ https://github.com/CEMES-CNRS/pymodaq_plugin_manager/blob/main/pymodaq_plugin_manager/doc/PluginList.md



Demonstration
*************

.. raw:: html

   <div style="text-align: center">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/ZdYpQIZHMCY" frameborder="0" allow="accelerometer;
     autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
   </div>


Information
***********

GitHub repo: https://github.com/CEMES-CNRS

Documentation: http://pymodaq.cnrs.fr/

List of available `plugins`__

Based on the ``pyqtgraph`` library : http://www.pyqtgraph.org by Luke Campagnola.

PyMoDAQ is written by Sébastien Weber: sebastien.weber@cemes.fr under a CeCILL-B license.

__ https://github.com/CEMES-CNRS/pymodaq_plugin_manager/blob/main/pymodaq_plugin_manager/doc/PluginList.md


Contribution
************

If you want to contribute see this page: :ref:`contributors`


They use it
***********
See :ref:`feedback`


Citation
********

By using PyMoDAQ, you are being asked to cite it (this website) when publishing results obtained with the help of its interface.
In that way, you're also helping in its promotion and amelioration.

Changelog
*********

Please see :doc:`the changelog </changelog>`.

.. toctree::
   :maxdepth: 6
   :caption: Contents:

   usage/Features
   usage/Installation
   usage/How_to_start
   usage/Description
   usage/CustomApp
   usage/tcpip
   usage/Feedback
   usage/Contributors
   usage/APIdoc

..   usage/classDiagram
   usage/APIdoc



Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
