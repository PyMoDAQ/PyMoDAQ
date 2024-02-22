.. _leco:

LECO communication
==================

If you want to control a device remotely, you can use `LECO <https://leco-laboratory-experiment-control-protocol.readthedocs.io>`_ - Laboratory Experiment Control Protocol.
Alternatively, you can use :ref:`tcpip`.

For that, you need to install the `pyleco <https://pypi.org/project/pyleco/>`_ package, for example via `pip install pyleco`.


Overview
--------

For remote control via LECO, you need three Components:

1. An *Actor*, which controls an instrument and can do *actions* on request,
2. A *Director*, which sends commands to the Actor and requests values for the Actor,
3. A *Coordinator* which transmits messages between Actors and Directors.


Coordinator
-----------

The *Coordinator* is the necessary infrastructure for the LECO network.
Therefore you should start it first.

You can start it executing `coordinator` in your terminal.


Actor
-----

Any control module from any plugins package can be made an Actor.

1. Start the module you want to control your instrument.
2. Select in the main settings the LECO options.
   - `Host` name and `port` are the host name and port of the Coordinator started above.
     If the Coordinator is on the same machine (i.e. localhost) and on the default port, you do not have to enter anything.
   - `Name` defines how this module should participate in the LECO network.
     If you leave it empty, the name of the module is taken.
3. Click on `connect`,
4. Now the green lamp should be lit and the Actor is ready to be used

.. note::

    You can change the name, even after having clicked connect.


Director
--------

For remote control, we need also the *Director* in order to direct the *Actor*.
You can start the *LECODirector* module from the mock plugins package, either in standalone mode or in the dashboard.

1. Start the appropriate type of LECODirector, either move or a viewer type.
2. Set the `Actor name` setting to the name of the actor module you wish to control.
3. Initialize the detector/actuator.
4. Read values or control the module remotely.


Developing with LECO for PyMoDAQ
--------------------------------

Here are some hints about the use of LECO in PyMoDAQ, that you might write your own programs.

Overview
........

Both, the *Actor* and the *Director* have a ``pyleco.Listener`` which offers some methods via JSON-RPC_, which is used by LECO.

.. _JSON-RPC: https://www.jsonrpc.org/specification

The Actor offers methods to do an action like initializing a movement or requesting a data readout.
After the movement or data acquisition has finished, it will call a method on some remote Component.
If you want, that the Actor sends the request to your Director, you have to tell the Actor about your name via the ``set_remote_name()`` method.

The :mod:`pymodaq.utils.leco.director_utils` module offers director classes, which makes it easier to call the corresponding methods of the Actor.

Serialization
.............

PyMoDAQ data objects have to be transferred between modules.
The payload of LECO messages are typically JSON encoded messages.
Therefore, the :class:`~pymodaq.utils.tcp_ip.serializer.Serializer` and :class:`~pymodaq.utils.tcp_ip.serializer.DeSerializer` can encode/decode the data objects to bytes.
For more information about serialization see :ref:`tcpip`.
In order to make a JSON string, base64 is used.
The Serializer offers the :meth:`~pymodaq.utils.tcp_ip.serializer.Serializer.to_b64_string` and the DeSerializer the :meth:`~pymodaq.utils.tcp_ip.serializer.DeSerializer.from_b64_string` method.
