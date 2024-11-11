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
   It seems like the */dev/ttyACM0* file is deleted each time we unplug the port, or shut down the computer. In this
   case the command should be run again.

Communicate to the board with Python
------------------------------------

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

Install the *pyfirmata2* Python package
+++++++++++++++++++++++++++++++++++++++

We suppose that we already installed Python and created an environment called *arduino_ubuntu* by following
:ref:`the installation instructions <quick_start>`.
