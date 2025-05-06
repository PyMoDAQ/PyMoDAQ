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
`Basler acA640-121gm <https://www.baslerweb.com/en/shop/aca640-121gm/>`_ camera with PyMoDAQ. This camera is very
common for example to image a laser beam.

.. figure:: /image/lab_story/basler/basler.png
   :width: 200

   Basler camera.

It uses the very nice PoE (power over ethernet) technology that allows to
transfer data and power with a single standard ethernet cable. We highly recommend to use ethernet connexion rather
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
plugging a simple USB that is automatically configured. We will see in this example that it can actually be very simple.

Here is a scheme of the network.

.. figure:: /image/lab_story/basler/connect_basler.svg
   :width: 500

   Local network to connect the camera to the computer. RJ45 = standard ethernet cable. The additional network interface
   controller (NIC) is necessary only if your computer has one embedded NIC (only one ethernet plug) that should be kept
   for internet connexion.

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
   :width: 200

   Startech USB 3.0 to Gigabit Ethernet NIC adapter.

Install the driver from Basler
------------------------------


