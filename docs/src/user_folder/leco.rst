.. _leco_communication:

LECO communication
==================

If you want to control a device remotely, you can use `LECO <https://leco-laboratory-experiment-control-protocol.readthedocs.io>`_ - Laboratory Experiment Control Protocol.

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
3. Click on `connect`, the green lamp should be lit and the Actor is ready to be used

.. note::

    You can change the name, even after having clicked connect.


.. _fig_leco_actor_daq_viewer:

.. figure:: /image/leco_communication/leco_actor_daq_viewer.png
    :alt: Mock plugin as a LECO Actor in a DAQ_Viewer

    Mock plugin as a LECO Actor in a DAQ_Viewer

Director
--------

For remote control, we need also the *Director* in order to direct the *Actor*.
You can start the *LECODirector* module from the mock plugins package, either in standalone mode or in the dashboard.

1. Start the appropriate type of LECODirector, either move or a viewer type.
2. Set the `Actor name` setting to the name of the actor module you wish to control.
3. Initialize the detector/actuator.
4. Read values or control the module remotely.

.. _fig_leco_director_daq_viewer:

.. figure:: /image/leco_communication/leco_director_daq_viewer.png
    :alt: Mock plugin as a LECO Director in a DAQ_Viewer

    Mock plugin as a LECO Director in a DAQ_Viewer

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

.. _leco_communication_serialization:

Serialization
.............

PyMoDAQ data objects have to be transferred between modules.
The payload of LECO messages are JSON encoded messages, which cannot hold objects such as
:class:`~pymodaq_data.data.DataToExport` or :class:`~pymodaq_data.data.DataActuator`.
Such objects are therefore encoded to bytes using the ``SerializableFactory`` of the
`serializall <https://github.com/PyMoDAQ/serializall>`_ package: its ``get_apply_serializer`` method converts a
registered object to bytes, and ``get_apply_deserializer`` converts the bytes back to the original object
(the type of the object is encoded in the first bytes).

These bytes are not inserted in the JSON message but sent as additional payload frames of the LECO message:
the JSON parameter is then set to ``None``. JSON compatible values (numbers, strings, lists...) are sent directly as
JSON parameters. The :func:`~pymodaq.utils.leco.utils.binary_serialization_to_kwargs` function prepares the
arguments accordingly (``data`` and ``additional_payload``) for pyleco's ``ask_rpc`` method.
