.. _smaract:

+------------------------------------+---------------------------------------+
| PyMoDAQ version                    | 5.3.9                                 |
+------------------------------------+---------------------------------------+
| Operating system                   | Ubuntu 24.04                          |
+------------------------------------+---------------------------------------+
| Last update                        | October 2026                          |
+------------------------------------+---------------------------------------+
| Difficulty                         | Easy                                  |
+------------------------------------+---------------------------------------+
| Cost                               | 4.000€                                |
+------------------------------------+---------------------------------------+

Move a SmarAct translation
==========================

In this example of use, we will see how to interface a
`SmarAct SLC <https://www.smaract.com/en/linear-stages/type/slc-series>`_ linear positioner with PyMoDAQ.
Those stages provide nanometer precision over a range that can extend up to several tens of centimeters, thanks to the
`piezo stick-slip technology <https://www.smaract.com/en/technology-introduction-and-options>`_.
They are
compact and of excellent quality. Quite a standard if one needs precise mechanics.
The cost for a controller and a stage with encoder would be about 4000€, but a controller can control at least 3 stages.
The SLC stages are the simplest actuators of SmarAct. The plugin may be able to control other kinds of actuators like
rotations for examples, but it is not guaranteed at the time of writing ;)

GIVE THE EXACT CONTROLLER + SENSOR MODULE + STAGE WE USE.

.. figure:: /image/lab_story/smaract/smaract_slc_stage.png
   :width: 300

   SmarAct SLC stage.

.. note::
   This documentation is presented for Ubuntu, but the procedure should be very similar for Windows.

Check that the controller is seen by the OS
--------------------------------------------

Before installing any software, let's verify that the MCS1 controller is recognised by Linux.
We plug it into a USB port and run:

.. code-block:: bash

   lsusb

We look for a new entry in the output when we plug/unplug the USB cable, in our case::

   Bus 002 Device 008: ID 0403:6001 Future Technology Devices International, Ltd FT232 Serial (UART) IC

If no new device appears, let's try a different USB cable or port and repeat.

.. note::
   On Windows, the equivalent check is the **Device Manager**.

Install the Linux driver (.so files)
------------------------------------

The SmarAct company provides the Linux driver with installation instructions.

.. figure:: /image/lab_story/smaract/linux_driver.png
   :width: 300

   Folder provided by the SmarAct company. The installation instructions are in the Readme-Linux.txt file.

In the /arch_x86_64/lib folder (x86_64 corresponding to our processor architecture) we found several .so files which
are the equivalent of .dll files on Windows. There are the libraries indispensable to communicate with the controller.

.. figure:: /image/lab_story/smaract/linux_libraries.png
   :width: 300

   Linux libraries.

.. note::
   The .so files are equivalent to .dll files on Windows.

We follow the installation instructions in the Readme-Linux.txt file and run the installer (bash script):

.. figure:: /image/lab_story/smaract/run_installer.png
   :width: 600

   Run the installer.

The script installs the libraries in /usr/lib:

.. figure:: /image/lab_story/smaract/libraries_installed.png
   :width: 450

   The libraries are now installed on our machine in /usr/lib.

The arrows at the right of the filename indicate that there is a link that point to the lastest version of the
library.

.. figure:: /image/lab_story/smaract/library_links.png
   :width: 450

   The .so file points towards the lastest version.

Install PyMoDAQ
---------------

The installation of PyMoDAQ is quite standard and mainly described in the :ref:`Quick start <ubuntu>`. Once it is
installed in a dedicated environment we install the SmarAct plugin:

``pip install pymodaq_plugins_smaract``

.. note::
   At the time of writing it installed pymodaq 5.3.9, pyqt 6.12.0 and pymodaq_plugins_smaract 5.3.0. If the build
   of the environment does
   not work properly at the time we read those lines, we can rebuild the exact same Python environment with the
   :download:`smaract_environment.yml <smaract_environment.yml>` and the command
   ``mamba env create -f smaract_environment.yml`` in a fresh environment.

Launch a DAQ_Move
-----------------

Once the installation is complete, let’s run a

``daq_move``

and follow those steps:

1. Select *SmarActMCS1*.
2. Show the settings.
3. Check that your controller is recognized with its serial number.
4. Select the axis where is plugged your actuator.
5. Connect to the actuator.
6. If the LED turns green we are happy :)
7. Set an absolute value.
8. Move to the set absolute value.

.. figure:: /image/lab_story/smaract/daq_move.png
   :width: 600

   DAQ_Move interface.

That's it! :)

WHAT HAPPENS IF MY CONTROLLER HAS MORE THAN 3 AXIS??
