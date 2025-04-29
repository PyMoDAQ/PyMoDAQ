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

PyMoDAQ installation
--------------------
