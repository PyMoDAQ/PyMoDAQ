.. _quick_start:

Quick Start
===========

PyMoDAQ installation on Windows is done in a few steps. We just need an internet connexion.

Python installation
-------------------

We first need to download the `Miniconda <https://docs.anaconda.com/miniconda/>`_ installer by clicking on the link
highlighted in red
in the following figure.

.. figure:: /image/quick_start/miniconda_installer_link.png

   Click on this link to start the download of *Miniconda*’s installer.

Let’s execute the installer and keep the default choices.

.. note::

   It will actually install in particular:

   * a **Python interpreter** (a *python.exe* file)
   * **conda**, which we will use exclusively as a *Python environment manager*
   * **pip**, which is a *Python package manager*

   We do not need to understand in details those notions for now.

Set up a new Python environment
-------------------------------

From the Windows *Start* menu, execute the *Anaconda Prompt*.

.. figure:: /image/quick_start/miniconda_prompt.png

   The Anaconda Prompt. The name in brackets at the beginning of the line indicates the *Python environment* that is
   currently activated. (base) indicates that we are in the default environment of *conda*.

In order to have a clean installation of PyMoDAQ on our machine, we isolate it in a dedicated Python environment.
Let’s execute the following command to create an environment called *pymodaq* with a 3.11 version of Python.

``conda create -n pymodaq python=3.11``

.. note::
   * We can call the environment as we wish.
   * As a rule of thumb, choose the second last version of Python to be sure that PyMoDAQ is compatible.

And let’s activate it.

``conda activate pymodaq``

After this command, we should notice that the name in brackets in the terminal is now *pymodaq*.

Install PyMoDAQ
---------------

After this preparation, the installation of PyMoDAQ is done with a single command line. It will take a few minutes to
download and install all the dependencies in our new environment.

``pip install pymodaq pyqt5``

Check the installation
----------------------

To check that the installation went well, we can execute a PyMoDAQ’s *control module* called
:ref:`DAQ_Move <DAQ_Move_module>`, using the
command

``daq_move``

This will prompt the following user interface. In the *Actuator* drop-down list, choose *Mock* and click
*Initialization*. This will simulate numerically the behavior of a simple actuator, with the reading of its position.
We can play a bit around to discover this module, and have a look at :ref:`the documentation <DAQ_Move_module>`.

.. figure:: /image/quick_start/mock_actuator.png

   The DAQ_Move module.

The basic installation is now complete! :)

Control a real instrument
-------------------------


