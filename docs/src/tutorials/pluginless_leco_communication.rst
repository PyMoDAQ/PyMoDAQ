pr.. _plugin_external_to_pymodaq:


Communication with devices outside of PyMoDAQ
=============================================
The preferred way of using a detector or an actuator with PyMoDAQ is of course to implement its instrument plugin,
as explained :ref:`in the plugin development page<plugin_development>`.
However, in some cases, one already has working devices included in a program written in another langage. In this 
tutorial we present how it is possible to incoporate such a program in the PyMODAQ ecosystem. Working things will
then be still used while benefiting all of PyMoDAQ's advantages: extensions, saving, etc.

There are  two different use cases: eiter your code is in python or it is not.

Python devices drivers without PyMoDAQ Plugin
------------------------------------------
If you are already communicating with devices in python and that the effort to translate them into pymodaq plugins
is too high (or time too short), you can easily connect them with the PymoDAQ ecosystem (even though it is *really*
recommended to implement their instrument plugin).

To do that, you'll have to install PyMoDAQ, this should install all PyMoDAQ packages and `pyleco <https://github.com/pymeasure/pyleco>`_.
You can then follow the example of the `qt-less standalone <https://github.com/PyMoDAQ/PyMoDAQ/blob/5.0.x/src/pymodaq/examples/qt_less_standalone_module.py>`_
to interface an actuator using your existing code with PyMoDAQ. Doing so results in a code similar to what you'll get by
writing a plugin, so once again it is advised to consider writing the plugin directly.

All of PyMoDAQ functionalities are available through this solution, except a local GUI for the device.
The LECODirector will still provide a remote GUI functionality, see :ref:`leco_communication` for more details.

Drivers in another language
---------------------------
The most interesting case and recommended use-case is if there's a part or all of your **already existing** setup
implemented in another language, for example in LabView. It becomes interesting if you want to benefit from the
PymoDAQ ecosystem and all the other existing instrument drivers/plugins.

You can then make your setup evolve without the hassle to extend your existing code but only rely on the PyMoDAQ
community's work!

As long as network capabilities are provided and a :term:`ZeroMQ` library is available, it is possible to connect to PyMoDAQ
through a minimal LECO  implementation and control your devices from PyMoDAQ.

Functionalities
~~~~~~~~~~~~~~~
The drawback of this approach is that not all PyMoDAQ functionalities are supported.

For detectors, 0D, 1D and 2D are supported, as well as multichannel. ND should work but wasn't tested.

For actuators, 0D, 1D and 2D are supported (even though the base GUI isn't fully compatible with more than 0D).
Multichannel (also called multiaxes) is not supported, but can be achieved by splitting a device by axe/channel and
present them individually to PyMoDAQ.

In both cases, exchanging settings **is not** supported.

LECO Protocol
~~~~~~~~~~~~~
LECO is a generic communication protocol to control experiments and measurement hardware and is the mean of communicating
with components outsides of PyMoDAQ. More detailed information can be found on the
`project page <https://leco-laboratory-experiment-control-protocol.readthedocs.io/en/latest/>`_. This page will provide
a basic explanation of LECO.

There are three essential and usefully LECO component interacting together in PyMoDAQ:
- Coordinator: an external program in charge of handling routing messages between nodes, using registered names. It can
be thought of as a switchboard operator when telephone companies employed them to let people speak to each other.
- Director: a LECO entity that consume data and control actors. It is integrated in PyMoDAQ as the
:ref:`LECODirector<leco_communication>` family of plugins. It can be thought of as a movie director, asking actors
to do something (*control*) and seeing their acting in return (*consume*).
- Actor: part of you program that produce data. It is linked to the device. It can be thought of as a movie actor,
acting like they've been told to (*producing data*).

.. _fig_leco_arch:

.. figure:: /image/tutorial_pluginless_leco/leco_arch.svg
    :alt: LECO Architecture

    LECO Architecture


In :numref:`fig_leco_arch` one can see the LECO network architecture. In this example, `Node 1` and `Node 2` are
LECO actors, each with instruments connected and a PyMoDAQ instance. They are connected to the coordinator, allowing
the directors on the `Main dashboard` to send command to control them and retrieve their data.


JSON-RPC
^^^^^^^^
LECO uses JSON-RPC to enable remote communication between distributed components. 
JSON-RPC is a way of achieving `Remote Procedure Calls (RPC) <https://en.wikipedia.org/wiki/Remote_procedure_call>`_
using JSON to encode exchanged messages.
It allows clients (Director) to call methods on a remote component (Actor) using standard JSON messages.

Example request:
::

    {
      "jsonrpc": "2.0",
      "method": "sign_in",
      "params": null,
      "id": 1
    }

Example response:
::

    {
      "jsonrpc": "2.0",
      "result": null,
      "id": 1
    }



However, in its integration with PyMoDAQ, pyleco can use supplementary binary data fields containing other types of data
all serialized as binary objects, with empty ``params`` and ``result`` fields in JSON requests and responses (as shown
on figure :ref:`fig_protocol_header` and explained in :ref:`leco_communication_serialization`).

.. _fig_protocol_header:

.. figure:: /image/tutorial_pluginless_leco/protocol_header.svg
    :alt: LECO Protocol Header

    LECO Protocol Header


When communicating with components outside of PyMoDAQ, pure JSON is used, meaning that ``params`` and ``results``
fields are used and the binary payload is left empty.

ZeroMQ (ZMQ)
^^^^^^^^^^^^
ZMQ is a high-level messaging library that simplifies communication over the network. It was the chosen networking
library for LECO. While it uses TCP under the hood, it hides the complexity of connection management and provides
a more abstract, message-oriented interface.

Unlike TCP, which is low-level, synchronous, and requires manual handling of connections, ZeroMQ is asynchronous and
handles connections, buffering, and reconnections automatically. It supports built-in communication patterns like
request/reply or publish/subscribe, making it easier to build distributed systems with few networking code.

In short, ZMQ simplifies socket communication making it a more developer-friendly messaging layer.

LECO protocol uses ZMQ sockets. Each Director/Actor open one ``DEALER`` type socket to connect to the Coordinator,
that listens using a ``ROUTER`` type socket. This is why the external implementation should have a ZMQ library, like
`LabView does <https://labview-zmq.sourceforge.io>`_.



Implementation guide
~~~~~~~~~~~~~~~~~~~~

To implement a plugin outside of PyMoDAQ, it is recommended to start by examining the `mock examples <https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples>`_.
A good approach is to use state machines (like LabView) to decide which messages are accepted —triggering corresponding
actions—, and which messages are declined —resulting in JSON-RPC error messages—, as this depends on the received message
and the current state.


.. _fig_state_machine_actuator:

.. figure:: /image/tutorial_pluginless_leco/state_machine_actuator.svg
    :alt: State machine for exchanged LECO messages with an actuator

    State machine for exchanged LECO messages with an actuator

.. _fig_state_machine_detector:

.. figure:: /image/tutorial_pluginless_leco/state_machine_detector.svg
    :alt: State machine for exchanged LECO messages with a detector

    State machine for exchanged LECO messages with a detector

:numref:`fig_state_machine_actuator` and :numref:`fig_state_machine_detector` represent the state machines used in the
mock examples implementation. They graphically represent the ``transitions`` attribute and the
``handle_trame`` method in the examples and represent valid transitions —or in other words the messages (RPC requests)
one can legally receive in a given state.

To understand a typical workflow and how the example code works, one can look at :numref:`fig_sequence_diagram_actuator`
and :numref:`fig_sequence_diagram_detector`. They're sequence diagrams of "classic" use-cases of an actuator and a
detector. In these diagrams links between ``Actor``, ``Director`` and ``Coordinator`` are LECO trames containing a
JSON-RPC request or response sent through a ZMQ socket.


.. _fig_sequence_diagram_actuator:

.. figure:: /image/tutorial_pluginless_leco/sequence_diagram_actuator.svg
    :alt: Sequence diagram for exchanged LECO messages with an actuator

    Sequence diagram for exchanged LECO messages with an actuator



.. _fig_sequence_diagram_detector:

.. figure:: /image/tutorial_pluginless_leco/sequence_diagram_detector.svg
    :alt: Sequence diagram for exchanged LECO messages with a detector

    Sequence diagram for exchanged LECO messages with a detector


Using these diagrams to understand the ``mock examples`` code and the state machines to list all possibilities, it
should be relatively easy to port for your setup. Once completed, please consider sharing your adaptation layer on
GitHub, as once done for a language, it is universal.

Compatibility
~~~~~~~~~~~~~
It is compatible with old Windows and python versions down to **Windows 7** and **Python 3.4** as long as one succeeds
in installing an old ``pyzmq`` version compatible with **Python 3.4** such as version **17**.

This means one could port their legacy setups to **PyMoDAQ** by writing the JSON-RPC communication layer and using an
up-to-date machine to control the setup using **PyMoDAQ** with most of its functionality available.