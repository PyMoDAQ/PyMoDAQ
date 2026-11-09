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

For this demonstration we used an MCS-6CC-USB-TAB controller (old version MCS1, now SmarAct sells MCS2 version),
an MCS-3S-EP-SDS15-TAB sensor module, and an SLC1740s
translation stage.

We suppose that the controller has already been configured.

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

System configuration
--------------------

Let's continue with the installation instructions. We still have two system files to create. Let's open the
file manager (*nautilus* in our case) with administrative privileges, so that we have the authorization on those files:

.. code-block:: bash

   sudo nautilus

The instructions say that "When an MCS controller is connected to the computer or switched on,
it is possible that the ftdi_sio driver is automatically loaded
for that device. In this case the application cannot connect to
the MCS. The kernel modules ftdi_sio and usbserial
must be unloaded before launching your application or blocked from
loading, e.g. by blacklisting them in /etc/modprobe.d/."

We thus create a blacklist-smaract.conf file in /etc/modprobe.d/, write those two lines and save:

.. code-block::

    blacklist ftdi_sio
    blacklist usbserial

.. figure:: /image/lab_story/smaract/modprobe.png
   :width: 600

Finally, we follow the last installation instruction: "The MCS Control library needs write access to the USB port the
MCS device is connected to. To automatically set r/w permissions when
an MCS is connected, a udev rule can be added to /etc/udev/rules.d/:
ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="666" "

We thus create a smaract.rules file in /etc/udev/rules.d directory, write the following line and save:

.. code-block::

    ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="666"

The *idVendor* and *idProduct* numbers correspond to the ones that are displayed with the *lsusb* command.

.. note::
   Be careful, it is important to use *curly brackets*!

.. figure:: /image/lab_story/smaract/rules.png
   :width: 600

.. note::
   It may be useful to restart the computer and the controller at this point.

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
