.. _arduino_ubuntu:

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| PyMoDAQ version                    | 4.4                                   |
+------------------------------------+---------------------------------------+
| Last update                        | november 2024                         |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+

Read an Arduino on Ubuntu
=========================

In this example of use, we will present how to read the temperature from an analogue output of an Arduino board with
PyMoDAQ installed on Ubuntu.

This example may be among the cheapest ways to test PyMoDAQ with an actual detector, as the only expenses are an
Arduino Uno
R3 board (30€) and a TMP36 sensor (1€). It will also be the opportunity to present some particularities related to the
use of an operating system based on Linux.

Install the Arduino IDE 2
-------------------------

The Arduino IDE is a GUI software that should be installed on our operating system to communicate with the board. We
follow
the instructions from
`this page <https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing/>`_.

Let's download the .AppImage file, which is equivalent to an .exe file on Windows.

.. figure:: /image/example/arduino_ubuntu/app_image.png

   Download the .AppImage file.

Once it is downloaded, right-click on the file, go to *Properties > Permissions* and tick *Allow executing as a file*.
This file can be placed wherever we like, we just need to double-click on it to launch the Arduino IDE.

Connect our Arduino to the computer
-----------------------------------

Let's connect our board on a USB port of the computer. Open a terminal and run the *lsusb* command, which will display
the devices that are connected on USB ports.

.. note::
   The name of this command can be decomposed as "ls"+"usb". The *ls* Bash command being used to see inside a folder.
Here it means "let me see the USB ports". It is equivalent as going into the *Devices & Printers* menu on Windows.

.. figure:: /image/example/arduino_ubuntu/arduino_lsusb_command.png

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
temperature of the TMP sensor, so we just bring him a 5V power, and connect its output (its central pin) to the A0
analog input of the
board. All the details should be found into the Arduino projects book.

.. figure:: /image/example/arduino_ubuntu/arduino_circuit.png

   Circuit of the Arduino board. The circuit inside the red rectangle is not used here.

Read the board with an Arduino sketch
-------------------------------------

A *sketch* is a script in the Arduino language to execute some commands on the board.

Let's try to upload the following sketch to the board by pressing the play button.

.. figure:: /image/example/arduino_ubuntu/arduino_sketch.png

   Reading of the TMP temperature with the Arduino IDE.

Once the upload is done, we can go to *Tools > Serial monitor*. It will display a new tab at the bottom of the window,
where we can read the temperature. We can check that it is not fake by pressing a finger on the TMP chip: the
temperature should rise.

It is probable that at the first try of uploading the sketch, we get an error saying that permission is denied on the
*/dev/ttyACM0* file. To get rid of this error, we need to give the proper rights so that the Arduino IDE will be
authorized to write into it. For that we can enter in a terminal the following command

``sudo chmod a+rw /dev/ttyACM0``

.. note::
   It seems like the */dev/ttyACM0* file is deleted each time we unplug the port, or shut down the computer. In those
   cases the command should be run again.

Speak to the board with Python
------------------------------

As we already noticed, the Arduino sketches are not natively written in Python. We will first have to make the
translation thanks to a
library called `pyFirmata2 <https://github.com/berndporr/pyFirmata2>`_, so that we can talk to the board with Python.

The communication is done in a client-server architecture: the server is the Arduino board, the client is our computer.
The installation of *Pyfirmata2* then goes into two steps: the upload of the *Standard Firmata* server to the board,
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

Install the *pyfirmata2* Python package
+++++++++++++++++++++++++++++++++++++++

We suppose that we already installed Python, created and activated an environment called *arduino_ubuntu* by following
:ref:`the installation instructions <quick_start>`.

We install *pyfirmata2* with *pip* in a terminal:

``pip install pyfirmata2``

Read the temperature with a Python script
+++++++++++++++++++++++++++++++++++++++++

We are now ready to read the temperature with a Python script! We will not start from scratch but rather use the
example script called
`print_analog_data.py <https://github.com/berndporr/pyFirmata2/blob/master/examples/print_analog_data.py>`_ available
in the examples of the library.

Let's download and run it in our *arduino_ubuntu* Python environment:

.. figure:: /image/example/arduino_ubuntu/arduino_pyfirmata_script.png

   Output of the *print_analog_data.py* script. We just changed the line 22 of the script to *self.samplingRate = 1*
   in order to get one reading per second, rather than 10 per second.

The number in the left column is the acquisition time, and the number in the right one is a float number proportional
to the voltage, itself proportional to the temperature.

We can check that if we unplug the pin A0, the output will be 0, and if we put the 5V from the Arduino directly on A0,
it outputs 1. To get the corresponding voltage, we thus use the following formula: *voltage = 5 x output*. To get the
reading in Celsius degree, we follow the procedure detailed in the Arduino projects book. In the end, we rewrite a bit
the *myPrintCallback* method as follow to get the temperature

.. figure:: /image/example/arduino_ubuntu/arduino_pyfirmata_callback.png

   Modification of the *myPrintCallback* method to get the output in Celsius degree.

We now get the output in Celsius degree!

.. figure:: /image/example/arduino_ubuntu/arduino_pyfirmata_script_celsius.png

   Output of the modified script. The raise in temperature happened when we put a finger on the TMP chip.

Speak to the board with PyMoDAQ
-------------------------------

.. note::
   The most straightforward way to read the board with PyMoDAQ should have been to install the
   `pymodaq_plugins_arduino <https://github.com/PyMoDAQ/pymodaq_plugins_arduino>`_ which already implements a 0D viewer
   to
   read the analogue outputs. However, at the time of writing the compatibility with Ubuntu is not guaranteed. This is
   thus
   left for further work.

We start from the
`pymodaq_plugins_template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_ and fork it on our remote repository,
following the procedure described in :ref:`Write and release a new plugin <new_plugin>`.