.. _arduino_ubuntu:

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| PyMoDAQ version                    | 4.4                                   |
+------------------------------------+---------------------------------------+
| Operating system                   | Xubuntu 22.04                         |
+------------------------------------+---------------------------------------+
| Last update                        | november 2024                         |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+

Read an Arduino on Ubuntu
=========================

In this example of use, we will present how to read an analogue output of an Arduino board with
PyMoDAQ installed on Ubuntu.

This example may be among the cheapest ways to test PyMoDAQ with an actual detector, as the only expenses are an
Arduino Uno
R3 board (30€) and a TMP36 sensor (1€), software included!
It will also be the opportunity to present some particularities related to the
use of an operating system based on Linux.

Prerequisite
------------

* :ref:`Story of an instrument plugin development <plugin_development>`
* :ref:`How to modify existing PyMoDAQ's code? <contribute_to_pymodaq_code>`
* :ref:`Write and release a new plugin <new_plugin>`

What we will learn
------------------

* Communicate with an Arduino board with Python
* Managing USB devices with Ubuntu
* Using a callback method for acquisition

Install the Arduino IDE 2
-------------------------

The Arduino IDE is a GUI software that should be installed on our operating system to communicate with the board. We
follow
the instructions from
`this page <https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing/>`_.

Let's download the .AppImage file, which is equivalent to a .exe file on Windows.

.. figure:: /image/lab_story/arduino_ubuntu/app_image.png

   Download the .AppImage file.

Once it is downloaded, right-click on the file, go to *Properties > Permissions* and tick *Allow executing as a file*.
This file can be placed wherever we like, we just need to double-click on it to launch the Arduino IDE.

Connect our Arduino to the computer
-----------------------------------

Let's connect our board on a USB port of the computer. Open a terminal and run the *lsusb* command, which will display
the devices that are connected on USB ports. This is the Linux equivalent to the *Devices settings* on Windows.

.. note::
   The name of this command can be decomposed as "ls"+"usb". The *ls* Bash command being used to see inside a folder.
   Here it means "let me see the USB ports". `This article <https://itsfoss.com/list-usb-devices-linux/>`_ details
   different ways to list the USB devices connected to a Linux system.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_lsusb_command.png

   Output of the *lsusb* command.

This way we have checked that our board is properly connected.

In the Arduino IDE menu, go to *Tools > Board* and select the correct model.

Go to *Tools > Port* and select the one that is proposed. It should be something like */dev/ttyACM0 (Arduino Uno)*.

.. note::
   If the *Tools > Port* menu is still empty at this stage, we may need to restart the IDE.

.. note::
   COM ports do not exist on a Linux system. Instead, once a USB port is connected, a file is created inside the */dev*
   folder, and the port name starts with */dev/tty...*.

Make our circuit
----------------

We mainly follow the *LOVE-O-METER* project of the
`Arduino projects book <https://www.uio.no/studier/emner/matnat/ifi/IN1060/v21/arduino/arduino-projects-book.pdf>`_.

We build the following circuit, without the LEDs part that is inside the red rectangle. We just want to read the
temperature of the TMP sensor, so we just bring him a 5V voltage, and connect its output (its central pin) to the A0
analog input of the
board. All the details should be found into the Arduino projects book.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_circuit.png

   Circuit of the Arduino board. The circuit inside the red rectangle is not used here.

Read the board with an Arduino sketch
-------------------------------------

A *sketch* is a script in the Arduino language to execute some commands on the board.

Let's try to upload the following sketch to the board by pressing the play button.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_sketch.png

   Reading of the TMP temperature with the Arduino IDE.

Once the upload is done, we can go to *Tools > Serial monitor*. It will display a new tab at the bottom of the window,
where we can read the temperature. We can check that it is not fake by pressing a finger on the TMP chip to
raise the temperature.

It is probable that at the first try of uploading the sketch, we get an error saying that permission is denied on the
*/dev/ttyACM0* file. To get rid of this error, we need to give the proper rights so that the Arduino IDE will be
authorized to write into it. For that we can enter in a terminal the following command

``sudo chmod a+rw /dev/ttyACM0``

.. note::
   It seems like the */dev/ttyACM0* file is deleted each time we unplug the port, or shut down the computer. In those
   cases the command should be run again.

.. note::
   On Linux systems, the `sudo <https://en.wikipedia.org/wiki/Sudo>`_ command means "I want administrator rights for
   the following command". It will therefore
   ask
   for our password.
   The `chmod <https://en.wikipedia.org/wiki/Chmod>`_ command is used to change the rights on files and folders.

Read the board with Python
--------------------------

As we already noticed, the Arduino sketches are not natively written in Python. We will first have to make the
translation thanks to a
library called `pyFirmata2 <https://github.com/berndporr/pyFirmata2>`_, so that we can talk to the board with Python.

The communication is done in a client-server architecture: the server is the Arduino board, the client is our computer.
The installation of pyFirmata2 then goes into two steps: the upload of the *Standard Firmata* server to the board,
which is done like any other sketch. And secondly, the installation of the Python package *pyfirmata2* in our
environment.

Install the *Firmata standard* server
+++++++++++++++++++++++++++++++++++++

We just need to upload a sketch that is already available through the Arduino IDE. So let's start it, and go to
*File > Examples > Firmata > StandardFirmata*. It will open a sketch that we have to upload to the board. That's it!

.. note::
   It happens while writing this tutorial that the board was giving a good temperature with the Arduino IDE, but output
   crazy values while using a Python script. In that case, it may be useful to upload again the Firmata server to the
   board.

Install the pyfirmata2 Python package
+++++++++++++++++++++++++++++++++++++

We suppose that we already installed Python, created and activated an environment called *arduino_ubuntu* by following
:ref:`the installation instructions <quick_start>`.

We install *pyfirmata2* with *pip* in a terminal:

``(arduino_ubuntu) pip install pyfirmata2``

Read the temperature with a Python script
+++++++++++++++++++++++++++++++++++++++++

We are now ready to read the temperature with a Python script! We will not start from scratch but rather use the
example script called
`print_analog_data.py <https://github.com/berndporr/pyFirmata2/blob/master/examples/print_analog_data.py>`_ available
in the examples of the library.

Let's download and run it in our *arduino_ubuntu* environment:

.. figure:: /image/lab_story/arduino_ubuntu/arduino_pyfirmata_script.png

   Output of the *print_analog_data.py* script. We just changed the line 22 of the script to *self.samplingRate = 1*
   in order to get one reading per second, rather than 10 per second.

The number in the left column is the acquisition time, and the number in the right one is a float number proportional
to the voltage, itself proportional to the temperature.

We can check that if we unplug the pin A0, the output will be 0, and if we put the 5V from the Arduino directly on A0,
it outputs 1. To get the corresponding voltage, we thus use the following formula: *voltage = 5 x output*. To get the
reading in Celsius degree, we follow the procedure detailed in the Arduino projects book. In the end, we rewrite a bit
the *myPrintCallback* method as follow to get the temperature

.. figure:: /image/lab_story/arduino_ubuntu/arduino_pyfirmata_callback.png

   Modification of the *myPrintCallback* method to get the output in Celsius degree.

We now get the output in Celsius degree!

.. figure:: /image/lab_story/arduino_ubuntu/arduino_pyfirmata_script_celsius.png

   Output of the modified script. The raise in temperature happened when we put a finger on the TMP chip.

Read the board with PyMoDAQ
---------------------------

Everything is now in our hands, we already know how to initiate the communication with the board, how to read its
outputs,
and how to close the communication with Python commands. This is all in the
pyFirmata2 example.
We will now put those commands in the proper methods of a PyMoDAQ instrument :term:`plugin`, the following table gives
an overview of the analogies between the
`print_analog_data.py <https://github.com/berndporr/pyFirmata2/blob/master/examples/print_analog_data.py>`_ file and
the
`daq_0Dviewer_ArduinoUbuntu.py <https://github.com/quantumm/pymodaq_plugins_arduino_ubuntu/blob/main/src/pymodaq_plugins_arduino_ubuntu/daq_viewer_plugins/plugins_0D/daq_0Dviewer_ArduinoUbuntu.py>`_
file. We'll explain how we arrived at this result below.

+------------------------------------+---------------------------------------+
| **print_analog_data.py**           | **daq_0Dviewer_ArduinoUbuntu.py**     |
+------------------------------------+---------------------------------------+
| PORT                               | PORT                                  |
+------------------------------------+---------------------------------------+
| AnalogPrinter                      | DAQ_0DViewer_ArduinoUbuntu            |
+------------------------------------+---------------------------------------+
| self.board                         | self.controller                       |
+------------------------------------+---------------------------------------+
| __init__                           | ini_detector                          |
+------------------------------------+---------------------------------------+
| start                              | grab_data                             |
+------------------------------------+---------------------------------------+
| myPrintCallback                    | callback                              |
+------------------------------------+---------------------------------------+

Install PyMoDAQ and create a new instrument plugin
++++++++++++++++++++++++++++++++++++++++++++++++++

.. note::
   The most straightforward way to read the board with PyMoDAQ could have been to install the
   `pymodaq_plugins_arduino <https://github.com/PyMoDAQ/pymodaq_plugins_arduino>`_ which already implements a 0D viewer
   to
   read the analogue outputs. However, at the time of writing the compatibility with Ubuntu is not guaranteed. This is
   thus
   left for further work.

Let's start by installing PyMoDAQ in our environment

``(arduino_ubuntu) $ pip install pymodaq pyqt5``

.. note::
   Version 4.4 at the time of writing.

* We start from the
  `pymodaq_plugins_template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_.
* We fork it on our remote repository with the name *pymodaq_plugins_arduino_ubuntu*.
* We clone it locally, for example with PyCharm (*File > Project from version control...* and enter the URL of our remote
  repository, see :ref:`How to modify existing PyMoDAQ's code? <contribute_to_pymodaq_code>`).
* We make an `editable install <https://setuptools.pypa.io/en/latest/userguide/development_mode.html>`_ in our
  environment with the following command:

``(arduino_ubuntu) $ pip install -e ~/PycharmProjects/pymodaq_plugins_arduino_ubuntu``

.. note::
   PyCharm will clone the repository in the ~/PycharmProjects directory.

Details about this procedure can be found in the tutorial :ref:`Write and release a new plugin <new_plugin>`.

What we want to read at each acquisition, the temperature, is a scalar, its dimensionality is 0. We must
therefore consider a OD viewer.

.. note::
   A camera for example, which would output a matrix of pixels at each acquisition, would be a 2D viewer.

We then have a series of renaming to do, as indicated in the following figure.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_plugin_arborescence.png

   Tree structure of our plugin. We have to be careful about the naming conventions of the files, folders, and class that
   are in red rectangles, even the case is sensitive.

If those naming conventions have been respected, then PyMoDAQ will detect our plugin. This can be easily tested by
running a :ref:`DAQ_Viewer module <DAQ_Viewer_module>` with the following command in our activated environment:

``(arduino_ubuntu) $ daq_viewer``

.. figure:: /image/lab_story/arduino_ubuntu/arduino_daq_viewer.png

   By running a DAQ_Viewer, we check that our plugin is recognized by PyMoDAQ.

Let's close this window after this check.

Initialization
++++++++++++++

We now have to implement the initialization of the communication.

The method *ini_detector* will be triggered when we click the
*Init. Detector* button. The corresponding method in the pyFirmata2 example is *__init__*.

First, we should import the *Arduino* object which establishes the bridge between our code and the acquisition card.

Secondly, we should get the name of the communication port opened with the board. This is done with the instruction
*PORT = Arduino.AUTODETECT*.

.. note::
   It seems important to put this instruction outside of the class.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_initialize_plugin.png

   Imports statements of the plugin.

We then modify the method *ini_detector* of our plugin class to put into *self.controller* the object that allows the
communication with the board, which is here *Arduino(PORT)*.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_ini_detector_method.png

   Minimal definition (without comments) of our *ini_detector* method, that will be triggered when the user click
   the *Init. detector* button.

A few attributes are also set in the *ini_attributes* method.

Running again a DAQ_Viewer and clicking the *Init. detector* button makes the LED turns green, we can proceed further!

.. note::
   Think about closing the window again.

Acquisition
+++++++++++

Let's now consider the acquisition. When the user will hit the *Play* button of the DAQ_Viewer interface, it will
trigger the *grab_data* method. Here again, we have to find inspiration from the pyFirmata2 example.

In this specific example, the acquisition is done with two methods: a main one (*start*), and a *callback* one
(*myPrintCallback*). This is specific
to pyFirmata2, which implements
`asynchronous <https://www.geeksforgeeks.org/synchronous-and-asynchronous-programming/>`_
methods to communicate with the board. In another context, this could be
useful if we would like our code to do something else in the dead times in between two calls of the board. We will not
enter into explaining what is asynchronicity here. The point is that it is easy to implement with PyMoDAQ: in the
*grab_data* method, we must choose the asynchronous way, and define a *callback* method, as we are invited to do in the
plugin template.

.. figure:: /image/lab_story/arduino_ubuntu/arduino_pymodaq_template.png

   The *grab_data* and *callback* methods from the *pymodaq_plugins_template*.

We end up with this implementation:

.. figure:: /image/lab_story/arduino_ubuntu/arduino_implement_grab.png

   The implementation of the acquisition in our plugin.

Let's run a DAQ_Viewer again!

.. figure:: /image/lab_story/arduino_ubuntu/arduino_it_works.png

   Reading of the temperature from the board with PyMoDAQ.

It works! :D

Conclusion
----------

This plugin is not well polished as it is. In particular, one should implement the *close* method of the plugin to
close the communication properly.

We can directly install this example from source with the command

``(arduino_ubuntu) $ pip install git+https://github.com/quantumm/pymodaq_plugins_arduino_ubuntu.git``

Hope you enjoyed it ;)

.. figure:: /image/lab_story/arduino_ubuntu/arduino_the_laughing_cow.jpg

   The Laughing Cow!
