.. _basler:

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| PyMoDAQ version                    | 4.4                                   |
+------------------------------------+---------------------------------------+
| Operating system                   | Ubuntu 24.04                          |
+------------------------------------+---------------------------------------+
| Last update                        | May 2025                              |
+------------------------------------+---------------------------------------+
| Difficulty                         | Easy                                  |
+------------------------------------+---------------------------------------+
| Cost                               | 400€                                  |
+------------------------------------+---------------------------------------+

Read a Basler camera
====================

In this example of use, we will see how simple it is to interface a
`Basler acA640-121gm <https://www.baslerweb.com/en/shop/aca640-121gm/>`_ camera with PyMoDAQ. This camera is quite cheap
(about 300€) and commonly used for example to image a laser beam. However, in principle, the procedure we will describe
in the following should work for any Basler camera, as Basler provides a common software interface called *Pylon*.

.. figure:: /image/lab_story/basler/basler.png
   :width: 200

   Basler camera.

This camera uses the very nice PoE (power over ethernet) technology that allows to
transfer data AND power with a single standard ethernet cable. We highly recommend to use ethernet connexion rather
than USB,
because the stability of the communication is much higher, and you can use a cable as long as you want! It is not the
industrial standard for nothing.
We will see that
it only requires to be careful to buy the correct ethernet switch.

.. note::
   This documentation is presented for Ubuntu, but it should be very similar for Windows.

Connect the camera to the computer
----------------------------------

With PoE, the connection of the camera to the computer is a bit more complicated than with USB. We will need to make a
local network with the computer and the camera. This is quite scary at first sight, since it requires more skills than
plugging a simple USB that is automatically configured. We will see in this example that it can actually be quite
simple. It is worth making the effort because the reward is high. After experiencing PoE, it is not possible to go back
to USB, guaranteed ;)

Here is a scheme of the network.

.. figure:: /image/lab_story/basler/connect_basler.svg
   :width: 500

   Local network to connect the camera to the computer. RJ45 = standard ethernet cable. The additional network interface
   controller (NIC) is necessary only if your computer has only one embedded NIC (only one ethernet plug) that should be
   kept for internet connexion.

First we need to purchase a PoE switch, we recommend for example the
`DLink DGS-1008P <https://www.dlink.com/en/products/dgs-1008p-8-port-gigabit-poe-unmanaged-switch>`_
, which has 4 PoE ports (we can
eventually plug up to 4 cameras) and 4 standard ethernet ports. The "unmanaged" option may be important since it
requires less configuration. The device is about 70€.

.. figure:: /image/lab_story/basler/poe_switch.png
   :width: 300

   DLink DGS-1008P. The 4 left ports are PoE, the 4 right ports are standard.

If our computer has only one ethernet plug (one embedded NIC) and we want to keep it for our internet connexion, we
recommend to use an external NIC that can be plugged on a USB port of our computer. This device is about 30€.

.. figure:: /image/lab_story/basler/external_nic.png
   :width: 150

   Startech USB 3.0 to Gigabit Ethernet NIC adapter.

Once our local network is built, we can proceed to the software installation.

Install the driver from Basler
------------------------------

We first have to download the *Pylon* software from Basler from
`this page <https://www.baslerweb.com/en/downloads/software/2012599532/>`_. In our case, since we are on Ubuntu, which
is a Debian-based Linux distribution, we will choose the Debian installer.
`Most probably, our processor architecture is x86_64 <https://www.redhat.com/en/topics/linux/ARM-vs-x86>`_, but we can
check that with the
`uname -m <https://www.howtogeek.com/how-to-use-the-uname-command-on-linux/>`_ command. So we are going to click on the
link framed in red.

.. figure:: /image/lab_story/basler/pylon_software.svg
   :width: 500

   Download *Pylon* software.

After filling a simple form, we can download the software. We will found, probably in our download folder, an archive
named *pylon-8.1.0_linux-x86_64_debs.tar.gz*. Let's right click and *Extract*, go into the folder and double-clic the
*pylon_8.1.0-deb0_amd64.deb* file. It will open the App Center of Ubuntu. Then click *Install*.

The installer created a *pylon* folder in the `/opt <https://www.baeldung.com/linux/opt-directory>`_
directory. Important executable files are in the */bin* subdirectory, we will be particularly interested in the
*PylonGigEConfigurator*.

.. figure:: /image/lab_story/basler/pylon_bin_directory.png
   :width: 500

   *Pylon* /bin subdirectory.

.. note::
   *bin* stands for *binary* which means executable files, or programs that are directly readable by the machine.

Let's open a terminal and cd into this directory to run this binary file with the *auto-ip* option. This program will
automatically scan our local network to see if there are Basler cameras plugged and attribute them an IP address.

.. figure:: /image/lab_story/basler/ip_configurator.svg
   :width: 800

   Run the PylonGigEConfigurator executable. It has seen our camera!

Now that the communication with our camera has been established, let's read it with PyMoDAQ!

Install PyMoDAQ
---------------

