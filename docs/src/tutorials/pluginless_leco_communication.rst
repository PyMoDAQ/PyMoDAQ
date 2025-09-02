.. _plugin_external_to_pymodaq:


Communication With Devices Outside of PyMoDAQ
=============================================
The preferred way of using a detector or an actuator with PyMoDAQ is of course to implement its instrument plugin,
as explained :ref:`in the plugin development page<plugin_development>`.
However, in some cases, one already has working devices included in a program written in another langage. In this 
tutorial we present how it is possible to incoporate such a program in the PyMODAQ ecosystem. Working things will
then be still used while benefiting all of PyMoDAQ's advantages: extensions, saving, etc.

There are  two different use cases: eiter your code is in python or it is not.

Python Devices Drivers Without PyMoDAQ Plugin
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

Drivers in Another Language
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
PyMoDAQ Dashboard instance, each with a set of Control/Instrument Modules corresponding to the devices (actors)
connected. They are connected to the coordinator over the network, allowing the directors on the `Main dashboard` to
send command to control them and retrieve their data.


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



Implementation Guide
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
We tested the communication by porting examples to **Python 3.4** on a **Linux** machine. It should be compatible down to
**Windows XP**, as long as one succeeds installing an old ``pyzmq`` version compatible with **Python 3.4**,
such as version **17** (*good luck though!*).

This means one could port their legacy setups to **PyMoDAQ** by writing the JSON-RPC communication layer and using an
up-to-date machine to control the setup using **PyMoDAQ** with most of its functionality available.



Here is a list of exchanged messages.

Network API Message Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All communication uses **LECO multipart frames** over ZMQ:

- ``[ version, receiver, sender, LECO header, payload ]``

  - ``version``: 1 byte (always ``b"\x00"``)
  - ``receiver``: UTF-8 string (e.g. ``"COORDINATOR"``)
  - ``sender``: UTF-8 string (device name)
  - ``LECO header``: 20 bytes = ``conversation_id`` (16B) + ``message_id`` (3B) + ``message_type`` (1B)
    - ``conversation_id`` can be randomly generated and should be the same for a conversation (a sequence of
    requests/responses) but can be changed between each next request if wanted.
    - ``message_id`` generaly starts at 0, but must stay the same between a request and its answer.
    - ``message_type`` is always JSON (value of ``1``)
        .. note::
            This specification is subject to change; please keep up to date with the
            `LECO documentation <https://leco-laboratory-experiment-control-protocol.readthedocs.io/en/latest/>`_
            and its `GitHub repository <https://github.com/pymeasure/leco-protocol>`_.
  - ``payload``: UTF-8 JSON (JSON-RPC 2.0)
  .. note::
     In the following message examples, given ``id`` values are not specific to the ``method``, the must remain
     the same between a method and its result, but could be any valid integer value.

Unless specified otherwise, a reponse is always sent to the ``sender`` of the request. Also, with asynchronous requests,
the receiver (probably a LECODirector) will always respond the asynchronous requests, either with empty responses or
with error messages. It is up to the developper to take them into consideration.


Here is a recap of JSON-RPC payload structure:

- Request:

.. code-block:: pseudojson

    {
      "id": <int>,
      "jsonrpc": "2.0",
      "method": "<name>",
      "params": { ... }
    }

- Expected Response:

.. code-block:: pseudojson

    {
      "id": <same>,
      "jsonrpc": "2.0",
      "result": <any|null>
    }

- Error:

.. code-block:: pseudojson

    {
      "id": null,
      "jsonrpc": "2.0",
      "error": { "code": <int>, "message": "<str>" }
    }



Message Summary
^^^^^^^^^^^^^^^^

**Common Messages**

.. list-table::
   :header-rows: 0
   :widths: 20 80


   * - :py:attr:`sign_in`
     - Registers a LECO component with the coordinator.
   * - :py:attr:`sign_out`
     - Unregister a LECO component with the coordinator.
   * - :py:attr:`set_remote_name`
     - Store the director name for asynchronous communication.
   * - :py:attr:`get_settings`
     - Request instrument settings (read/write) from LECODirector.
   * - :py:attr:`pong`
     - Check if a LECO component is alive.
   * - :py:attr:`rpc.discover`
     - Not implemented; calling it returns an error.

**Actuator Messages**

.. list-table::
   :header-rows: 0
   :widths: 20 80

   * - :py:attr:`move_home`
     - Move actuator to home setpoint; async updates via send_position/set_move_done.
   * - :py:attr:`move_abs`
     - Move actuator to absolute position; async updates as above.
   * - :py:attr:`move_rel`
     - Move actuator by relative delta; async updates as above.
   * - :py:attr:`stop_motion`
     - Stop any ongoing movement immediately.
   * - :py:attr:`get_actuator_value`
     - Request current actuator value; async updates include set_units and send_position.

**Detector Messages**

.. list-table::
   :header-rows: 0
   :widths: 20 80

   * - :py:attr:`send_data_grab`
     - Ask data from detector repeatedly until stop_grab.
   * - :py:attr:`send_data_snap`
     - Ask data from detector once.
   * - :py:attr:`stop_grab`
     - Stop detector acquisition.


**Error Messages**

.. list-table::
   :header-rows: 0
   :widths: 20 80

   * - :py:attr:`invalid_request`
     - Error message returned when request is invalid in current state.



Common Messages
^^^^^^^^^^^^^^^
These are the messages used in both actuator and detector communication.



.. py:attribute:: sign_in
Registers a LECO component with the coordinator. It is sent to ``receiver="COORDINATOR"`` and is the only message where
communication is initiated by the device. It sends the sign_in request and receive either a valid response or an error
when the name is already taken.

- Request:

 .. code-block:: json

     {
       "id": 1,
       "jsonrpc": "2.0",
       "method": "sign_in",
       "params": {}
     }

- Expected Response:

 .. code-block:: json

     {
       "id": 1,
       "jsonrpc": "2.0",
       "result": null
     }

- Error:

 .. code-block:: json

     {
       "id": null,
       "jsonrpc": "2.0",
       "error": {
         "code": -32091,
         "message": "The name is already taken."
       }
     }




.. py:attribute:: sign_out
Unregister a LECO component with the coordinator. It is crucial to try as much as possible to send the message as it
will otherwise keep the name unusable for at least a few minutes.

- Request:

 .. code-block:: json

     {
       "id": 2,
       "jsonrpc": "2.0",
       "method": "sign_out",
       "params": {}
     }

- Expected Response:

 .. code-block:: json

     {
       "id": 2,
       "jsonrpc": "2.0",
       "result": null
     }




.. py:attribute:: set_remote_name
Most instrument data shared between LECO components is shared asynchronously, thus an actor will need to initiate
communication with a director. Using this method, an actor stores the name of the director to which it should
send requests in the future.

- Request:

 .. code-block:: json

     {
       "id": 3,
       "jsonrpc": "2.0",
       "method": "set_remote_name",
       "params": {"name": "<remote>"}
     }

- Expected Response:

 .. code-block:: json

     {
       "id": 3,
       "jsonrpc": "2.0",
       "result": null
     }




.. py:attribute:: get_settings
Ask for the instrument settings, so that they can be accessed (read/write) by the LECODirector. The easiest is to send
an empty JSON object, as settings are expected to use binary serialization. Doing so makes it impossible to access the
settings on the Director side. **It's a known limitation of communication with non PyMoDAQ components**.

- Request:

 .. code-block:: json

     {
       "id": 4,
       "jsonrpc": "2.0",
       "method": "get_settings",
       "params": {}
     }

- Expected Response:

 .. code-block:: json

     {
       "id": 4,
       "jsonrpc": "2.0",
       "result": {}
     }




.. py:attribute:: pong
A method sent by the coordinator to check if a LECO component is still alive, after a moment of inactivity.

- Request:

 .. code-block:: json

     {
       "id": 5,
       "jsonrpc": "2.0",
       "method": "pong",
       "params": {}
     }

- Expected Response:

 .. code-block:: json

     {
       "id": 5,
       "jsonrpc": "2.0",
       "result": null
     }




.. py:attribute:: rpc.discover
Not implemented and it should not even be called. Response can be an error:

.. code-block:: json

   {
     "id": null,
     "jsonrpc": "2.0",
     "error": {
       "code": -1,
       "message": "NotImplemented"
     }
   }

Actuator Messages
^^^^^^^^^^^^^^^^^
Messages only used when communicating with an actuator.


.. py:attribute:: move_home
A request to ``move_home``, i.e. to move to a setpoint value. A first request is sent, then the reponse is sent. In the
background, the request to move is sent to the actuator. Until the target value is reached (or a ``stop_move`` is
received), the actuator is probed and its value is sent to the ``remote name`` stored after ``set_remote_name``,
periodicaly, using the ``send_position`` request. Once done moving, the final value is sent with ``set_move_done``.

Actuator values are generaly 0D and if PyMoDAQ's daq_move GUI is used, they should be 0D. However, if used
programmatically, to build extensions or other virtual devices, exchanging 0D, 1D, and 2D actuator values is allowed.

- Request:

.. code-block:: json

    {
      "id": 6,
      "jsonrpc": "2.0",
      "method": "move_home",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 6,
      "jsonrpc": "2.0",
      "result": null
    }

- Async device-initiated messages:

.. code-block:: pseudojson

    {
      "jsonrpc": "2.0",
      "method": "send_position",
      "params": {"data": {"position": <current>}}
    }

.. code-block:: pseudojson

    {
      "jsonrpc": "2.0",
      "method": "set_move_done",
      "params": {"data": {"position": <final>}}
    }


.. py:attribute:: move_abs
Similar to ``move_home``, except that an absolute value to reach is sent in the first request.

- Request:

.. code-block:: pseudojson

    {
      "id": 7,
      "jsonrpc": "2.0",
      "method": "move_abs",
      "params": {"position": <number|2D array>}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 7,
      "jsonrpc": "2.0",
      "result": null
    }

- Async: same sequence of ``send_position`` then ``set_move_done``.



.. py:attribute:: move_rel
Similar to ``move_home``, except that a relative value to reach is sent in the first request.

- Request:

.. code-block:: pseudojson

    {
      "id": 8,
      "jsonrpc": "2.0",
      "method": "move_rel",
      "params": {"position": <delta number|2D array>}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 8,
      "jsonrpc": "2.0",
      "result": null
    }

- Async: same sequence of ``send_position`` then ``set_move_done``.



.. py:attribute:: stop_motion
A request to stop a ``move_*`` action if one is occuring. The movement should be stopped before sending the response.

- Request:

.. code-block:: json

    {
      "id": 9,
      "jsonrpc": "2.0",
      "method": "stop_motion",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 9,
      "jsonrpc": "2.0",
      "result": null
    }




.. py:attribute:: get_actuator_value
A request to ask for the current value. First the response is sent. Then, the actuator is probed and its units are sent
(if it uses units) as a parameter of ``set_units``. Finally, its value is sent with ``send_position``.

- Request:

.. code-block:: json

    {
      "id": 10,
      "jsonrpc": "2.0",
      "method": "get_actuator_value",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 10,
      "jsonrpc": "2.0",
      "result": null
    }

- Async:

.. code-block:: json

    {
      "jsonrpc": "2.0",
      "method": "set_units",
      "params": {"units": "<str>"}
    }

.. code-block:: pseudojson

    {
      "jsonrpc": "2.0",
      "method": "send_position",
      "params": {"data": {"position": <current>}}
    }



Detector Messages
^^^^^^^^^^^^^^^^^
Messages only used when communicating with a actuator.


.. py:attribute:: send_data_grab
Ask data from a detector. First the actor should send its response. Then in background, using
the ``remote name`` stored after ``set_remote_name``, ``set_data`` requests are sent periodically, with ``data`` as a
parameter.

It continues until a ``stop_grab`` request is received.

``<RawDetectorData>`` is a 0, 1 or 2D data array, depending on the detector. When using multichannel, it gets
wrapped in another layer of array corresponding the channels. So ``[<RawDetectorData>, <RawDetectorData>]`` for two
channels, where each ``<RawDetectorData>`` is of a shape matching the expected detector dimension.

.. note::
    ND data should also work but was not tested!

- Request:

.. code-block:: json

    {
      "id": 11,
      "jsonrpc": "2.0",
      "method": "send_data_grab",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 11,
      "jsonrpc": "2.0",
      "result": null
    }

- Async (repeated):

.. code-block:: pseudojson

    {
      "jsonrpc": "2.0",
      "method": "set_data",
      "params": {
        "data": {
          "data": <RawDetectorData>,
          "axes": [ {"data":[...], "units":"...", "label":"..."} ], # Optional
          "labels": ["ch0", ...], # Optional
          "multichannel": <bool> # Optional if false
        }
      }
    }


.. py:attribute:: send_data_snap
Same as ``send_data_grab`` but only once.

- Request:

.. code-block:: json

    {
      "id": 12,
      "jsonrpc": "2.0",
      "method": "send_data_snap",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 12,
      "jsonrpc": "2.0",
      "result": null
    }

- Async (single):

.. code-block:: pseudojson

    {
      "jsonrpc": "2.0",
      "method": "set_data",
      "params": {
        "data": {
          "data": <RawDetectorData>,
          "axes": [ {"data":[...], "units":"...", "label":"..."} ], # Optional
          "labels": ["ch0", ...], # Optional
          "multichannel": <bool> # Optional if false
        }
      }
    }


.. py:attribute:: stop_grab
The request sent when the acquisition should stop. The detector should stop acquiring and send data before responding to
this request.
- Request:

.. code-block:: json

    {
      "id": 13,
      "jsonrpc": "2.0",
      "method": "stop_grab",
      "params": {}
    }

- Expected Response:

.. code-block:: json

    {
      "id": 13,
      "jsonrpc": "2.0",
      "result": null
    }


Error Messages
^^^^^^^^^^^^^^

.. py:attribute:: invalid_request

When a request is not supposed to be received in the current state according to :numref:`fig_state_machine_actuator`
and :numref:`fig_state_machine_detector`, one should still answer but with an error:

.. code-block:: json

    {
      "id": null,
      "jsonrpc": "2.0",
      "error": {
        "code": -100,
        "message": "Request received is invalid in current state."
      }
    }

.. note::
    ``message`` and ``code`` values are user-defined.

