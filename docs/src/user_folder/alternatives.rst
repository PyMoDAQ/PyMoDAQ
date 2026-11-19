.. _alternatives:

PyMoDAQ and other instrument control tools
==========================================

PyMoDAQ is not the only Python tool to control instruments and acquire data. The tools below solve different problems
at different levels, and they are often used together. This page says what each one is for, so that you can pick the
right one, or a combination, for your experiment.

Three levels
------------

Projects in this field sit at one of three levels, and a project often includes (fully or partly) the level below:

* **Instrument drivers and communication**: talk to one instrument (PyVISA, pylablib, the vendor libraries).
* **Laboratory experiments**: operate several instruments together, scan, display and save data (PyMoDAQ, PyMeasure, NOMAD CAMELS,
  QCoDeS).
* **Large instruments and facilities**: control systems for many devices, running around the clock
  (Tango Controls, EPICS with Bluesky/Ophyd).

In short
--------

.. list-table::
   :header-rows: 1
   :widths: 14 12 30 22 22

   * - Tool
     - Level
     - What it is
     - Pick it when
     - Look elsewhere when
   * - **PyMoDAQ**
     - Lab experiment
     - A framework with a graphical Dashboard: instrument plugins, live viewers for 0D to ND data, scans, HDF5
       saving, scripting and remote control
     - you want a GUI to drive a mix of cameras, spectrometers, stages, power meters, digitizers... and to scan, log
       and save data without writing the interface
     - you only need a few commands on one instrument, or you run a facility-wide control system
   * - **PyVISA**
     - Communication
     - A Python layer over the VISA standard to talk to GPIB, USB, serial and Ethernet instruments
     - an instrument speaks SCPI-like text commands and you want to script it
     - you want a GUI, a data model, synchronized acquisition or scans
   * - **pylablib**
     - Drivers (and utilities)
     - A library of Python drivers (cameras, stages, oscilloscopes, lasers, spectrometers...) with data processing
       helpers and a small set of Qt GUI tools
     - you want a ready-made driver for a camera or a stage in a script
     - you want a complete acquisition application
   * - **PyMeasure**
     - Lab experiment
     - Instrument classes, plus an *experiment* API: a measurement is a procedure whose parameters, live plots and
       queue of runs are generated as a GUI
     - your measurements are parameter sweeps of electrical or SCPI-type instruments, one procedure per experiment
     - your data are images or other multidimensional arrays, or several detectors have to be shown and
       synchronized live
   * - **NOMAD CAMELS**
     - Lab experiment
     - A configurable measurement application (University of Erlangen-Nuremberg, FAIRmat consortium): measurement
       protocols assembled from steps in a GUI, recorded with their metadata in HDF5 following the FAIR principles,
       with a link to the NOMAD platform
     - you want to define protocols graphically and keep complete, self-describing records of every measurement
     - you want to see and process multidimensional data live while acquiring it
   * - **QCoDeS**
     - Lab experiment
     - A Python data acquisition framework (instrument drivers, parameters, measurement contexts, a database of runs),
       developed by a consortium of quantum computing groups (Copenhagen, Delft, Sydney, Microsoft)
     - you write your measurements as Python code, sweeping parameters and recording every run to a database
     - you need a ready-made multi-instrument GUI, or your instruments are mostly cameras and optical devices
   * - **Tango Controls**
     - Facility
     - A free and open-source device-oriented control system with device servers, with full support for C++, Python and
       Java, used by tens of sites, mostly large research facilities
     - you operate a facility with many devices and users and need a common control system
     - you are a single lab starting from a handful of USB or Ethernet instruments
   * - **Bluesky / Ophyd**
     - Facility
     - Libraries to run experiments (plans executed by a RunEngine) on top of device abstractions (Ophyd), developed
       at Brookhaven National Laboratory and mostly used with EPICS
     - you run a beamline or a facility, mostly with EPICS, and want reusable plans with rich metadata and streaming data
     - you are a single lab starting from a handful of USB or Ethernet instruments

.. note::

   This comparison tries to be fair and is based on the public documentation of each project, but it may be
   incomplete, outdated or wrong on some points, and it comes from the PyMoDAQ side. Each of these tools evolves:
   check their documentation, and `open an issue <https://github.com/PyMoDAQ/PyMoDAQ/issues>`_ or a pull request if
   you find an error.

PyVISA and pylablib: the driver level
-------------------------------------

`PyVISA <https://pyvisa.readthedocs.io>`_ opens a session to an instrument (through a VISA library supplied by an
instrument vendor, or the pure Python ``pyvisa-py`` backend) and lets you write and read messages. It is the right tool to learn what an instrument
answers, or to write a ten-line script. `pylablib <https://pylablib.readthedocs.io>`_ provides device classes for many
instruments, in particular cameras and translation stages, and some helpers to process and store data.

Neither knows what an experiment is: no common interface for all the instruments, no synchronization between them and
no saving. PyMoDAQ does not compete with them, it builds on them: many PyMoDAQ instrument plugins use PyVISA, pylablib
(this is for instance how several camera plugins, such as the Thorlabs or Andor ones, drive their hardware) or a vendor
library, and add what is missing on top (see :doc:`/developer_folder/plugin_cookbook`). If you already have driver
code for an instrument, wrapping it in a plugin gives you the GUI, the scans and the saving for it.

PyMeasure, NOMAD CAMELS and QCoDeS: measurements as procedures
--------------------------------------------------------------

These three tools are organized around the *measurement procedure*: you describe what a measurement does (the
parameters to sweep, the quantities to record), and the tool runs it and records the results.

`PyMeasure <https://pymeasure.readthedocs.io>`_ is a package that makes measurements easy to set up and run with
limited coding. It has a repository of instrument classes and an experiment API where a *procedure* (its parameters,
how it runs) is turned into a GUI with live graphs and a queue of experiments. It is well suited to an experiment that
is a sweep over parameters of electrical instruments.

`NOMAD CAMELS <https://fau-lap.github.io/NOMAD-CAMELS/>`_ is of the same family, with the procedure built graphically:
a protocol is assembled from steps (loops, sweeps, conditions, function calls) without programming, and run with its
instrument settings and code recorded in an HDF5 file, with an emphasis on FAIR metadata and on the NOMAD platform for
research data management. It can connect to EPICS and to generic drivers (including cameras through openCV and
pylablib).

`QCoDeS <https://microsoft.github.io/Qcodes/>`_ models instruments as collections of *parameters*, defines
measurements as sweeps of parameters, and stores every run in a database. It comes with drivers for
instruments from many vendors (Keysight, Keithley, Rohde & Schwarz, Zurich Instruments...) and live plotting with
Plottr. QCoDeS is code first and database centered, PyMoDAQ is GUI first and file (HDF5) centered. PyMoDAQ can be
scripted (:doc:`/user_folder/scripting`), but if you never want a GUI and already have QCoDeS drivers for all your
instruments, QCoDeS is the more direct path.

PyMoDAQ is organized differently: around the instruments and the data they produce rather than around the procedure.
Its strength is the data model and the live display. Whatever the instrument produces (an electrical signal, a
pressure, a waveform, an image, a hyperspectral cube), it is an instance of the same generic data object, with its
axes and units, from the plugin to the HDF5 file, through the graphical viewers and the data analysis tools
(:doc:`/data_management/data_objects`). Together with acquisition in real time, this makes the live visualization of
data of any dimension a basic feature rather than an add-on. Instruments are handled through a common contract
(actuators and detectors), so that scans, loggers and other extensions work with any of them.

Tango and Bluesky: facility scale
---------------------------------

`Tango Controls <https://www.tango-controls.org>`_ is a free, open-source, device-oriented control system with full
support for C++, Python and Java, used by tens of sites, mostly large research facilities, to run accelerators and
experiments around the clock. `Bluesky <https://blueskyproject.io/bluesky/>`_ separates *what to do* (plans, written as
Python generators) from *how to do it* (a RunEngine, the interpreter of plans, acting on
`Ophyd <https://blueskyproject.io/ophyd/>`_ devices) and streams metadata and data to callbacks (plots, databases, files) as it runs; Ophyd implements the device interface
for EPICS hardware.

These systems are built for installations with many devices running continuously, and they come with an
infrastructure to set up (device servers, or EPICS and the services around Bluesky) that is more than a lab with a few
instruments usually needs. PyMoDAQ is installed with ``pip`` and runs on a laptop connected to the instruments. The levels are complementary rather than exclusive: a laboratory setup can be one of the clients of a
facility control system. There is today no plugin exposing Tango devices in PyMoDAQ, and how to use Tango or Bluesky
devices from PyMoDAQ is an open question being explored. PyMoDAQ can itself be driven remotely, through
:doc:`/user_folder/leco`.

Other projects
--------------

Other open-source projects in this field, each with its own focus:

* `ScopeFoundry <https://www.scopefoundry.org>`_: a Python platform to control custom laboratory experiments and
  visualize scientific data, used for scanning microscopy.
* `yaq <https://yaq.fyi>`_: a modular and extensible instrument control framework.
* `labscript suite <https://labscriptsuite.org>`_: composing, running and analyzing precisely hardware-timed
  experiments, mostly in quantum science.
* `ARTIQ <https://m-labs.hk/experiment-control/artiq/>`_: a control system for quantum information research,
  mostly used in atomic physics, for real-time sequencing.

Where PyMoDAQ is a good choice
------------------------------

* A mixed set of instruments (cameras, spectrometers, motion controllers, power meters, oscilloscopes, DAQ cards...)
  to be used together from a single interface.
* Experiments where you want to *see* the data while acquiring (0D, 1D, 2D and ND viewers, ROIs, math on the data),
  whatever the instrument: from a single value or a waveform to an image or a hyperspectral cube.
* Step scans of one or several actuators with one or several detectors, with the result saved in HDF5 with its axes
  and units, and logging of slowly varying signals.
* Teams where people who are not programmers operate the setup: an *experiment* file restores the whole
  configuration, and writing a plugin for a new instrument is the only coding needed.
* Domain specific acquisition and orchestration. PyMoDAQ separates the instruments, handled by the Dashboard, from the
  *actions* performed with them, which are the extensions (:doc:`/user_folder/extensions`). Some extensions stay
  generic (scans, logging, PID, optimization) while others are very focused on a field, such as the ones of
  `PyMoDAQ Femto <https://pymodaq-femto.readthedocs.io/en/latest/>`_ (ultrafast optics) or of
  `PyMoDAQ BeamShaping <https://pymodaq-plugins-beam-shaping.readthedocs.io/en/latest/>`_, so that the same instruments
  can be orchestrated for the specificity of your field.
* A framework to build your own application: the same widgets, data classes and modules can be reused in a custom
  application (:doc:`/developer_folder/custom_app`).

Where it is not
---------------

* Hard real-time control and precisely timed pulse sequences (microseconds and below): PyMoDAQ runs Python with a Qt
  event loop. Keep such loops in the instrument (FPGA, microcontroller, vendor controller, or a system built for it
  such as ARTIQ or the labscript suite) and use PyMoDAQ to configure and monitor them.
* Experiments with a single instrument and a one-off script: PyVISA, pylablib or the vendor Python package is lighter.
* Facility-wide infrastructure with queues and many users: Tango or Bluesky/Ophyd are designed for it.
* An instrument with no plugin yet needs one to be written. See :doc:`/tutorials/first_plugin`: a complete plugin
  is typically under 80 lines. The list of existing plugins is in the
  `plugin manager <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_.

Combining them
--------------

The tools are complementary. Typical combinations are PyVISA or pylablib inside a PyMoDAQ plugin, a PyMoDAQ detector
whose plugin wraps a QCoDeS or PyMeasure instrument driver, or PyMoDAQ instruments published over LECO and driven from
a script written by the user.
