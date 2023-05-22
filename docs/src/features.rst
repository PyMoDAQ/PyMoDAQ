PyMoDAQ's overview
==================

.. _overview:

.. figure:: /image/overview.png
   :alt: overview

   PyMoDAQ control of an experimental setup using the Dashboard and a set of DAQ_Viewer and DAQ_Move modules


PyMoDAQ is an advanced user interface to control instruments (casually called Detectors)  and actuators (sometimes
called Moves for historical reasons). Each of these will have their own interface called :ref:`DAQ_Viewer_module` and
:ref:`DAQ_Move_module` that are always the same (only some specifics about communication with the controller will differ),
so that a PyMoDAQ's user will always find a known environment independent of the kind of instruments it controls. These
detectors and actuators are grouped together in the :ref:`Dashboard_module` and can then be controlled manually by
the user: acquisition of images, spectra... for various
positions of the actuators (see :numref:`overview`). The Dashboard has functionalities to fully configure
all its detectors and actuators and
save the configuration in a file that will, at startup, load and initialize all modules. Then
Dashboard's extensions can be used to perform advanced and automated tasks on the detectors and actuators
(see :numref:`overview_submodules_bis`):

* The first of these extensions is called :ref:`DAQ_Scan_module` and is used to perform automated and synchronized data
  acquisition as a function of multiple actuators *positions*. Many kind of *scans* are possible: 1Ds, 2Ds, NDs, set of
  points and many ways to perform each of these among which :ref:`adaptive_scans` scan modes have been recently developed
  (from version 2.0.1).
* The second one is the :ref:`DAQ_Logger_module`. It is a layer between all the detectors within the dashboard and various ways
  to log data acquired from these detectors. As of now, one can log to :

  * a local binary hdf5 file
  * a distant binary hdf5 file or *same as hdf5* but on the cloud (see `HSDS from the HDF group`__ and the `h5pyd`__ package)
  * a local or distant SQL Database (such as PostgreSQL). The current advantage of this solution is to be able to access
    your data on the database from a web application such as `Grafana`__. Soon a tutorial on this!!
* Joystick control of the dashboard actuators (and eventually detectors).
* PID closed loop interface
* Direct code execution in a Console

   .. _overview_submodules_bis:

.. figure:: /image/pymodaq_diagram.png
   :alt: overview

   PyMoDAQ's Dashboard and its extensions: DAQ_Scan for automated acquisitions, DAQ_Logger for data logging and many other.



__ https://www.hdfgroup.org/solutions/highly-scalable-data-service-hsds/
__ https://github.com/HDFGroup/h5pyd
__ https://grafana.com/grafana/

..
    Here is a poster of PyMoDAQ features (to be updated).


       .. _figure_Main_diagramm:

    .. figure:: ../image/pymodaq_diagram.png
       :alt: PyMoDAQ

       PyMoDAQ features: Control modules within a DashBoard and its extensions

    :download:`Download as pdf <../image/pymodaq_diagram.png>`