.. _alternatives:

PyMoDAQ and other instrument control tools
==========================================

PyMoDAQ is not the only Python tool to control instruments and acquire data. Each of the tools below solves a
different problem, and they are often used together. This page says what each one is for, so that you can pick the
right one, or a combination, for your experiment.

In short
--------

.. list-table::
   :header-rows: 1
   :widths: 16 28 28 28

   * - Tool
     - What it is
     - Pick it when
     - Look elsewhere when
   * - **PyMoDAQ**
     - A framework with a graphical Dashboard: instrument plugins, live viewers, scans, HDF5 saving, scripting and
       remote control
     - you want a GUI to drive a mix of cameras, spectrometers, stages, power meters, digitizers... and to scan,
       log and save data without writing the interface, in a lab or an instrumentation team
     - you only need to send a few commands to one instrument, or you run a multi-user facility based on EPICS
   * - **PyVISA**
     - A Python layer over the VISA standard to talk to GPIB, USB, serial and Ethernet instruments
     - you have an instrument that speaks SCPI-like text commands and you want to script it
     - you want a GUI, a data model, synchronized acquisition or scans out of the box
   * - **QCoDeS**
     - A Python data acquisition framework (instrument drivers, parameters, measurement contexts, a SQLite
       database), widely used in quantum and condensed matter devices labs
     - you work mostly in Jupyter notebooks or scripts, sweeping parameters and recording to a database
     - you need a ready-made multi-instrument GUI, or your instruments are mostly cameras and optical devices
   * - **Bluesky / Ophyd**
     - A set of libraries to run experiments (plans executed by a RunEngine) on top of device abstractions, developed
       at synchrotron facilities, with EPICS as a main control system
     - you run a beamline or a facility, with EPICS, a queue of experiments, several users and a data catalog
     - you are a single lab starting from a handful of USB or Ethernet instruments

PyVISA: the communication layer
-------------------------------

`PyVISA <https://pyvisa.readthedocs.io>`_ opens a session to an instrument (through the NI-VISA library or the pure
Python ``pyvisa-py`` backend) and lets you write and read messages. It is the right tool to learn what an instrument
answers, or to write a ten-line script.

PyVISA does not know what a camera, an axis or a measurement is: there is no interface, no data structure, no
synchronization between instruments and no saving. PyMoDAQ does not compete with it, it builds on it: many PyMoDAQ
instrument plugins use PyVISA (or a vendor library, or a serial port) to talk to the hardware, and add what is
missing on top (see :doc:`/developer_folder/plugin_cookbook`). If you already have PyVISA code for an instrument,
wrapping it in a plugin gives you the GUI, the scans and the saving for it.

QCoDeS: parameters, measurements and a database
-----------------------------------------------

`QCoDeS <https://microsoft.github.io/Qcodes/>`_ models instruments as collections of *parameters*, defines
measurements as sweeps of parameters, and stores every run in a SQLite database with its metadata. It comes with
many drivers for electronic instruments (source meters, lock-in amplifiers, cryogenic equipment...) and is typically
driven from Jupyter notebooks or scripts, with plotting tools around it.

QCoDeS and PyMoDAQ overlap on scans and data storage and differ in approach: QCoDeS is code first and database
centered, PyMoDAQ is GUI first and file (HDF5) centered, with actuators and detectors as the two basic
concepts and with detectors that return images, spectra and other multidimensional data with their axes as well as
single values. PyMoDAQ can be scripted (:doc:`/user_folder/scripting`), but if you never want a GUI and already have
QCoDeS drivers for all your instruments, QCoDeS is the more direct path.

Bluesky and Ophyd: experiments at facility scale
------------------------------------------------

`Bluesky <https://blueskyproject.io/bluesky/>`_ separates *what to do* (plans, written as Python generators) from
*how to do it* (a RunEngine acting on `Ophyd <https://blueskyproject.io/ophyd/>`_ devices) and emits a stream of
documents that can be saved to a catalog. Together with EPICS and the other Bluesky project tools, it is built for
beamlines and facilities: many devices, many users, queued and remotely monitored experiments, reproducible plans.

That power comes with an infrastructure to set up (typically EPICS, a message bus, a data store) which is more than
a lab with a few instruments needs. PyMoDAQ is installed with ``pip`` and is usable within the hour on a laptop
connected to the instruments. PyMoDAQ can also be driven remotely, through :doc:`/user_folder/leco`.

Where PyMoDAQ is a good choice
------------------------------

* A mixed set of instruments (cameras, spectrometers, motion controllers, power meters, oscilloscopes, DAQ cards...)
  to be used together from a single interface.
* Experiments where you want to *see* the data while acquiring (0D, 1D, 2D and ND viewers, ROIs, math on the data).
* Step scans of one or several actuators with one or several detectors, with the result saved in HDF5 with its axes
  and units, and logging of slowly varying signals.
* Teams where people who are not programmers operate the setup: an *experiment* file restores the whole
  configuration, and writing a plugin for a new instrument is the only coding needed.
* A framework to build your own application: the same widgets, data classes and modules can be reused in a custom
  application (:doc:`/developer_folder/custom_app`).

Where it is not
---------------

* Hard real-time control loops (microseconds): PyMoDAQ runs Python with a Qt event loop, keep such loops in the
  instrument (FPGA, microcontroller, vendor controller) and use PyMoDAQ to configure and monitor them.
* Experiments with a single instrument and a one-off script: PyVISA or the vendor Python package is lighter.
* Facility-wide infrastructure based on EPICS, with queues and many users: Bluesky/Ophyd is designed for it.
* An instrument with no plugin yet needs one to be written. See :doc:`/tutorials/first_plugin`: a complete plugin
  is typically under 80 lines. The list of existing plugins is in the
  `plugin manager <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_.

Combining them
--------------

The tools are complementary. Typical combinations are PyVISA inside a PyMoDAQ plugin, a PyMoDAQ detector
whose plugin wraps a QCoDeS instrument driver, or PyMoDAQ instruments published over LECO and driven from a
script written by the user.
