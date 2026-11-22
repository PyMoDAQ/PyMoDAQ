.. _release_5_1:

==========================
PyMoDAQ 5.1 (5.1.0-5.1.13)
==========================

PyMoDAQ 5.1.0 was released on 2025-10-06, followed by thirteen maintenance releases until 2026-06-17. Pull requests
(#NNN) refer to the `PyMoDAQ repository <https://github.com/PyMoDAQ/PyMoDAQ>`_.

.. contents::
   :local:
   :depth: 2

Highlights
==========

5.1 consolidates the LECO remote-control layer, generalizes **optimizers** (with the Bayesian optimizer rebuilt on
version 2 of the ``bayesian-optimization`` package) and adds a **Data Mixer** and an **adaptive scan mode** as
extensions. DAQ_Move gets a more compact layout and a relative-move UI, and units are handled more consistently.

Major new features
==================

Optimizers and extensions
-------------------------

* Integration of the ``bayesian-optimization`` package v2: #534; generalization of the optimizer framework: #581;
  base model corrections and logo: #730, #732
* **Adaptive scan** mode as an extension: #589; detectors can be overridden from an extension: #588, #727
* **Data Mixer** in the core extensions: #719
* PID upgrade and documentation, setpoint actuators usable from extensions: #703, #708, #633
* **Stop type** setting for optimizers, with a dynamic tooltip: #731, #726

LECO communication
------------------

* LECO serializer, units for moves, settings of LECO plugins and grab/stop in the viewer: #553, #554, #558
* Controller host IP settable from the director, actor/director connecting to an arbitrary coordinator host and
  port: #557, #689
* More robust directors, improvements of the LECO parts, JSON data with ``LECODirector``: #683, #678, #627
* Compatibility with ``pyleco`` >= 0.5: #644; documentation for JSON communication: #709

Control modules and UI
----------------------

* **Compact actuators** layout: #592; **relative** UI for DAQ_Move: #641; actuator UI type selectable in the
  Dashboard: #676; patches of the actuator UI: #619
* Control module settings as a popup (``viewer/settings_as_popup`` config entry): #620
* Notification when a live Viewer2D cannot display all the received data: #570
* Dashboard can be run directly with a preset from the command line: #665, #670
* Units: SI prefix handling for dimensionless quantities, units kept as is, optional SI prefix display, units in
  scans: #604, #625, #626, #704
* Nested group parameters (``addMenu``) with a compatible default preset: #712, #716; list ordering instead of
  values in the configuration: #673
* Name for the scan and logger windows: #711; h5 browser features moved to ``pymodaq_gui``: #546
* Configuration file split by package, with checks of mandatory entries: #593, #594, #606

Documentation
-------------

* *Lab story* "Read a Basler camera", rewritten "Loading modules" section, fixed sequence diagrams: #612, #677, #707,
  #713

Bug fixes (5.1.1-5.1.13)
========================

* **5.1.1-5.1.2**: documentation builds, daq_logger quit, dashboard module loading factorization: #737, #743, #749,
  #728
* **5.1.3-5.1.4**: .NET libraries initialization, ``pyqtgraph`` restricted to < 0.14, monorepo port: #745, #768,
  #780, #789
* **5.1.5**: Python 3.9 support removed and 3.13 added, configuration list entries, average live plot display: #795,
  #803, #827
* **5.1.6-5.1.7**: DAQ_Move dataset, ``QPointF`` access, ``QTimer`` ownership, loading a dashboard with a preset:
  #818, #854, #872, #876
* **5.1.8-5.1.9**: LECODirector timers and control, wrong plot of 2D spread scans, ``tables < 3.10`` security
  fix: #885, #894, #896, #904
* **5.1.10-5.1.11**: non-printable characters in XML export, preset settings restoration, scanner data
  initialization, dynamic data casting in the viewer: #932, #950, #959, #960
* **5.1.12**: 10+ actuators/detectors in an experiment, ``ini_position`` button moves to the initial scan position:
  #1053, #1057
* **5.1.13**: sub-package versions forced to match the ``pymodaq`` version: #1082
