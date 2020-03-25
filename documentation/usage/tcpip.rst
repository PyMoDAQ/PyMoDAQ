.. _tcpip:

TCP/IP communication
====================

This section is for people who want an answer to: *I have a detector or an actuator controlled on a distant computer and
cannot have it on the main computer, do you have a solution?*

The answer is of course : *YES*

From version 1.6.0, each actuator (DAQ_Move) or detector (DAQ_Viewer) module can be connected to their counterpart on a
distant computer. For both modules, a TCPServer plugin is available and can be initialized. It will serve as a bridge
between the main computer, running for instance a DAQ_Scan module, and the distant one running a usual DAQ_Move or DAQ_Viewer
module, see :numref:`tcpip_scheme`. Every parameter of the distant module will be exported on its server counterpart. Any modification
of these parameters, either on the server or on the local module, will be updated on either the local module or the server.


   .. _tcpip_scheme:

.. figure:: /image/tcpip.png
   :alt: tcpip

   Typical configuration with modules on distant computers communicating over a TCP/IP connection


The TCP_server plugin could also be used as a bridge between PyMoDAQ and another custom software (installed locally or
on a distant computer) able to initialize a TCP client and understand PyMoDAQ's TCP/IP communications. For instance, at
CEMES, we've build such a bridge between Digital Micrograph running (eventually) on a distant computer and controlling
a specific Gatan camera on an electron microscope.