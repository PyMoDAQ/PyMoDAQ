.. _leco_component_mixin:

Making a PyMoDAQ Component Available Through LECO
==================================================

This page is a developer guide explaining how to expose a new PyMoDAQ component
over the `LECO`_ network.  The ``DashBoard`` class is used as a running example
throughout.

A second section covers the **scripting side**: once a component is LECO-enabled,
how to control it from a plain Python script without a PyMoDAQ GUI.

.. _LECO: https://leco-laboratory-experiment-control-protocol.readthedocs.io

.. seealso::

   :ref:`leco_communication` for the end-user guide (connecting the UI, starting
   the Coordinator, using the LECODirector plugins).

   :ref:`plugin_external_to_pymodaq` for communicating with non-Python devices
   over LECO.


Architecture
~~~~~~~~~~~~~

.. figure:: /image/component_leco/leco_scripting_architecture.svg
   :alt: LECO scripting architecture in PyMoDAQ
   :align: center
   :width: 150%
   :class: no-max-width-figure

   Architecture of LECO in PyMoDAQ and of the scripting layer.  A plain Python
   script instantiates a wrapper (the Director side) that starts its own ``Listener`` and ``Director``,
   connects to the LECO Coordinator, and communicates with the running
   PyMoDAQ component (the Actor side) over the network.

Part 1 – LECO-Enabling a Component (PyMoDAQ Side)
--------------------------------------------------

The process has five steps:

1. Inherit from :class:`~pymodaq.utils.leco.pymodaq_listener.LECOComponentMixin`
   and implement its abstract methods.
2. Define the command and RPC-method name enumerations.
3. Register incoming RPC methods in :class:`~pymodaq.utils.leco.pymodaq_listener.ActorHandler`.
4. Add outgoing message handling in
   :class:`~pymodaq.utils.leco.pymodaq_listener.ActorListener.queue_command`.
5. Implement ``process_leco_commands`` on the component.


Step 1 – Inherit ``LECOComponentMixin``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your class must also be a ``QObject`` (or inherit from one), because
``_leco_commands_signal`` is a Qt ``Signal``. Pass the listener class to use
to ``LECOComponentMixin.__init__``. Also the ``QObject`` inheritance **must**
be before the ``LECOComponentMixin`` one, and the constructor call after.

.. note::

   ``QObject.__init__`` calls ``super()`` so it follows the class MRO.
   If ``LECOComponentMixin`` appears before ``QObject`` in the inheritance
   order, its ``__init__`` may be invoked without the required
   ``listener_class`` argument, leading to initialization errors.

.. code-block:: python

   from pymodaq.utils.leco.pymodaq_listener import LECOComponentMixin, ActorListener
   from pymodaq_utils.utils import ThreadCommand
   from qtpy.QtCore import Signal

   class MyComponent(SomeQObjectBase, LECOComponentMixin):

       _leco_commands_signal = Signal(ThreadCommand)  # required

       def __init__(self, ...):
           LECOComponentMixin.__init__(self, MyComponentActorListener)
           SomeQObjectBase.__init__(self, ...)

Then implement the three abstract methods:

.. code-block:: python

   def get_leco_name(self) -> str:
       return "my_component"      # unique name on the LECO network, static or defined by constructor

   def get_leco_host_port(self) -> tuple[str, int]:
       return "localhost", 12300  # Coordinator address, generally from some settings or configuration

   def process_leco_commands(self, status: ThreadCommand) -> None:
       ...  # see Step 5

Then ``connect_leco(True)`` can be user when ready to join the network (e.g. at startup or
on a button click) and ``connect_leco(False)`` to disconnect.

For example,  ``DashBoard`` inherits both ``CustomApp`` and
``LECOComponentMixin``, passes ``DashboardActorListener``, and calls
``connect_leco(True)`` automatically during ``do_things_after_ui_setup``.

.. warning::

    All listeners (``DashboardActorListerner``, ``MoveActorListener``, ...)
    are actually aliases for ``ActorListener``

Step 2 – Define Command Enumerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two sets of names are needed:

* **RPC method names** (strings exchanged over the network) – defined in
  :mod:`pymodaq.utils.leco.rpc_method_definitions` as ``StrEnum`` subclasses.
* **ThreadCommand names** (used internally to cross the Qt thread boundary) –
  defined in :mod:`pymodaq.utils.leco.pymodaq_listener`.

However, they are generally the same names.

For each new component you need one enum for incoming commands (Director →
Actor, i.e. what your component *receives*) and one for outgoing commands
(Actor → Director, i.e. what your component *sends back*):

.. code-block:: python

   # in rpc_method_definitions.py
   class MyComponentMethods(StrEnum):
       DO_SOMETHING   = "do_something"    # incoming: Director calls this on the Actor
       GET_INFO       = "get_info"

   class MyComponentDirectorMethods(StrEnum):
       SOMETHING_DONE = "something_done"  # outgoing: Actor calls this on the Director
       SEND_INFO      = "send_info"


   # in pymodaq_listener.py
   class LECOMyComponentCommands(StrEnum):
       # incoming (RPC → ThreadCommand)
       DO_SOMETHING   = "do_something"
       GET_INFO       = "get_info"
       # outgoing (ThreadCommand → RPC)
       SOMETHING_DONE = "something_done"
       SEND_INFO      = "send_info"

**Dashboard example** – :class:`~pymodaq.utils.leco.rpc_method_definitions.DashboardMethods`
contains ``GET_DEVICES``, ``GET_CONFIGURATIONS``, ``APPLY_CONFIGURATION``,
``GET_PRESETS``, ``APPLY_PRESET``.
:class:`~pymodaq.utils.leco.rpc_method_definitions.DashboardDirectorMethods`
contains ``SEND_DEVICES``, ``SEND_CONFIGURATIONS``, ``SEND_PRESETS``,
``APPLIED_CONFIGURATION_DONE``, ``APPLIED_PRESET_DONE``.
Both mirror each other in
:class:`~pymodaq.utils.leco.pymodaq_listener.LECODashboardCommands`.


Step 3 – Register Incoming RPC Methods in ``ActorHandler``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Modify :class:`~pymodaq.utils.leco.pymodaq_listener.ActorHandler` to
register new RPC methods. Use ``register_binary_rpc_method`` when the argument needs binary
(de)serialisation and ``register_rpc_method`` otherwise.  Each method body emits a
``ThreadCommand`` on ``self.signals.cmd_signal`` to hand the call over to the
Qt thread.

.. code-block:: python

   class ActorHandler:
       def register_rpc_methods(self) -> None:
           ...
           self.register_rpc_method(self.do_something,
                                    name=MyComponentMethods.DO_SOMETHING)
           self.register_rpc_method(self.get_info,
                                    name=MyComponentMethods.GET_INFO)

       def do_something(self, value: str) -> None:
           self.signals.cmd_signal.emit(
               ThreadCommand(LECOMyComponentCommands.DO_SOMETHING, attribute=value)
           )

       def get_info(self) -> None:
           self.signals.cmd_signal.emit(ThreadCommand(LECOMyComponentCommands.GET_INFO))

   class MyActorListener(ActorListener):
       def __init__(self, name, **kwargs):
           super().__init__(name, handler_class=MyActorHandler, **kwargs)

**Dashboard example** – ``get_devices``,
``get_configurations``, ``apply_configuration``, ``get_presets``,
``apply_preset`` were added to ``ActorHandler``.  Each simply emits the matching
``LECODashboardCommands`` on ``cmd_signal``:

.. code-block:: python

   def get_devices(self):
       self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.GET_DEVICES))

   def apply_preset(self, preset: str):
       self.signals.cmd_signal.emit(
           ThreadCommand(LECODashboardCommands.APPLY_PRESET, attribute=preset)
       )

   ...


Step 4 – Handle Outgoing Messages in ``queue_command``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ActorListener.queue_command`` is the outgoing channel: it receives
``ThreadCommand`` objects emitted on ``_leco_commands_signal`` and translates
them into ``ask_rpc`` calls sent to the Director.  Add ``elif`` branches for
your new commands:

.. code-block:: python

   # in your MyActorListener (or patched into ActorListener)
   def queue_command(self, command: ThreadCommand) -> None:
       ...
       elif command.command == LECOMyComponentCommands.SOMETHING_DONE:
           self.send_rpc_message_to_remote(
               method=MyComponentDirectorMethods.SOMETHING_DONE,
               result=command.attribute,   # plain JSON value
           )
       elif command.command == LECOMyComponentCommands.SEND_INFO:
           # binary payload example
           self.send_rpc_message_to_remote(
               method=MyComponentDirectorMethods.SEND_INFO,
               **binary_serialization_to_kwargs(command.attribute, data_key="data"),
           )
       else:
           super().queue_command(command)

.. info::
   ``binary_serialization_to_kwargs`` (from
   :mod:`pymodaq.utils.leco.utils`) returns either
   ``{"data": <json_value>, "additional_payload" : None}`` for plain Python types or
   ``{"data": None, "additional_payload": [<bytes>]}`` for PyMoDAQ
   objects that need binary serialisation (``DataActuator``,
   ``DataToExport``, ...).

**Dashboard example** – the relevant branches in
:meth:`~pymodaq.utils.leco.pymodaq_listener.ActorListener.queue_command`:

.. code-block:: python

   elif command.command == LECODashboardCommands.SEND_DEVICES:
       self.send_rpc_message_to_remote(
           method=DashboardDirectorMethods.SEND_DEVICES,
           **binary_serialization_to_kwargs(command.attribute, data_key="data"),
       )
   elif command.command == LECODashboardCommands.SEND_CONFIGURATIONS:
       self.send_rpc_message_to_remote(
           method=DashboardDirectorMethods.SEND_CONFIGURATIONS,
           configurations=command.attribute,   # plain list, no serialisation needed
       )
   elif command.command == LECODashboardCommands.APPLIED_PRESET_DONE:
       self.send_rpc_message_to_remote(
           method=DashboardDirectorMethods.APPLIED_PRESET_DONE,
           done=command.attribute,
       )


Step 5 – Implement ``process_leco_commands``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This slot runs in the Qt thread and is called whenever the background
``ActorListener`` delivers an incoming command.  Dispatch on
``status.command`` and either:

* **Return a result immediately** – emit the reply command directly on
  ``_leco_commands_signal``.
* **Start a process** – trigger an internal action; emit the reply command
  once the action completes.

.. code-block:: python

   def process_leco_commands(self, status: ThreadCommand) -> None:
       if status.command == LECOMyComponentCommands.DO_SOMETHING:
           # start a process; the reply will be emitted when it finishes
           self.do_something_async(status.attribute)  # will later emit SOMETHING_DONE

       elif status.command == LECOMyComponentCommands.GET_INFO:
           # return result immediately
           info = self.compute_info()
           self._leco_commands_signal.emit(
               ThreadCommand(LECOMyComponentCommands.SEND_INFO, info)
           )

**Dashboard example**:

.. code-block:: python

   def process_leco_commands(self, status: ThreadCommand) -> None:
       if status.command == LECODashboardCommands.GET_DEVICES:
           # returns immediately
           devices = {
               'actuators': [m.get_leco_name() for m in self.actuators_modules],
               'detectors': [m.get_leco_name() for m in self.detector_modules],
           }
           self._leco_commands_signal.emit(
               ThreadCommand(LECODashboardCommands.SEND_DEVICES, devices)
           )
       elif status.command == LECODashboardCommands.GET_PRESETS:
           # returns immediately
           self._leco_commands_signal.emit(
               ThreadCommand(LECODashboardCommands.SEND_PRESETS,
                             self.preset_manager.entries)
           )
       elif status.command == LECODashboardCommands.APPLY_PRESET:
           # asynchronous: preset loading triggers a callback that later emits
           # APPLIED_PRESET_DONE once the preset has been loaded
           preset = status.attribute
           self._scripted_preset_load = True
           self.preset_manager.execute_entry_base(preset)
       ...
   ...
   def do_things_after_preset(self, preset_name: str):
        ...
        # returns the loaded preset value here
        if self._scripted_preset_load:
            self._scripted_preset_load = False
            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.APPLIED_PRESET_DONE, True))

Once all of that is done, your component is available through LECO with the sets or methods you defined.


Part 2 – Scripting LECO-Enabled Components
-------------------------------------------

Once a component is LECO-enabled you can control it from a plain Python script
without any PyMoDAQ GUI, by writing a **mini LECO Director**.  The scripting
utilities live in :mod:`pymodaq.scripting`.


A scripting wrapper:

1. Creates a :class:`pyleco.utils.listener.Listener` that registers on the
   LECO network under a unique name (e.g. ``scripting_<device_name>``).
2. Registers the **Director-side callback methods** on that listener so that
   asynchronous replies from the Actor are received.
3. Obtains a ``communicator`` from the listener and wraps it in a
   :class:`pyleco.directors.director.Director` pointed at the target Actor.
4. Exposes each Actor command as a Python method that:

   a. Creates a :class:`~concurrent.futures.Future`.
   b. Calls ``set_remote_name`` so the Actor knows where to reply.
   c. Calls ``self._director.ask_rpc(method, ...)`` to send the command.
   d. Returns the ``Future`` (caller can ``.result()`` to block).

The callback methods resolve the ``Future`` when the Actor's asynchronous reply
arrives.

Writing a New Scripting Wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is a minimal skeleton, using the Dashboard as example:

.. code-block:: python

   import atexit
   from concurrent.futures import Future, InvalidStateError
   from pyleco.directors.director import Director
   from pyleco.utils.listener import Listener
   from serializall import SerializableFactory

   sf = SerializableFactory()

   class MyComponentScriptWrapper:
       def __init__(self, actor_name: str = "my_component", **kwargs):
           self._actor_name = actor_name
           self._some_result_future: Future | None = None

           # 1 – start a listener (the scripting side)
           self._listener = Listener(name=f"scripting_{actor_name}", timeout=None)
           self._listener.start_listen()

           # 2 – register Director-side callbacks
           self._listener.register_rpc_method(self.something_done)
           # for binary replies use register_binary_rpc_method:
           # self._listener.register_binary_rpc_method(self.some_data, accept_binary_input=True)

           # 3 – get a communicator and a Director
           self._communicator = self._listener.get_communicator()
           self._director = Director(actor=actor_name,
                                     communicator=self._communicator, **kwargs)
           atexit.register(self.close)

       def close(self):
           self._director.ask_rpc('sign_out', actor='COORDINATOR')
           self._listener.close()
           self._director.close()
           self._communicator.close()

       def _set_remote_name(self):
           self._director.ask_rpc('set_remote_name', name=f"scripting_{self._actor_name}")

       # ---- commands sent to the Actor ----

       def do_something(self, value: str) -> Future[str]:
           future = Future()
           self._some_result_future = future
           self._set_remote_name()
           self._director.ask_rpc("do_something", value=value)
           return future

       # ---- callbacks received from the Actor ----

       def something_done(self, result: str) -> None:
           try:
               self._some_result_future.set_result(result)
               self._some_result_future = None
           except (InvalidStateError, AttributeError):
               pass

Binary replies (e.g. a ``DataToExport``) require ``register_binary_rpc_method``
and deserialization:

.. code-block:: python

   # registration
   self._listener.register_binary_rpc_method(self.set_data, accept_binary_input=True)

   # callback
   def set_data(self, data=None, additional_payload=None) -> None:
       value = sf.get_apply_deserializer(additional_payload[0])
       try:
           self._snap_future.set_result(value)
           self._snap_future = None
       except (InvalidStateError, AttributeError):
           pass

Sending binary data to the Actor (e.g. ``move_abs`` with a ``DataActuator``):

.. code-block:: python

   def move_abs(self, value: DataActuator) -> Future[DataActuator]:
       future = Future()
       self._move_done_future = future
       self._set_remote_name()
       self._director.ask_rpc(
           "move_abs",
           position=None,
           additional_payload=[sf.get_apply_serializer(value)],
       )
       return future


Using the Wrapper in a Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the wrapper in place, scripts are straightforward.  Calling ``.result()``
on a ``Future`` blocks until the Actor replies:

.. code-block:: python

   from pymodaq.scripting import Actuator, Detector, Dashboard

   # connect to a running Dashboard and load a preset
   dashboard = Dashboard()
   dashboard.apply_preset('default').result()

   # get all loaded modules
   devices = dashboard.get_scripting_devices()
   theta  = devices['actuators']['Angle']
   camera = devices['detectors']['Camera']

   # blocking move, then async snaps
   pos = theta.move_abs('90°').result()
   frame = camera.snap().result()

The built-in :class:`~pymodaq.scripting.devices.Actuator`,
:class:`~pymodaq.scripting.devices.Detector`, and
:class:`~pymodaq.scripting.devices.Dashboard` classes in
:mod:`pymodaq.scripting` follow exactly this pattern and cover all existing
LECO-enabled PyMoDAQ components. To add a new component, write a wrapper
similar to :class:`~pymodaq.scripting.utils.LECODeviceWrapper` and expose it
through a lightweight public class (like ``Actuator`` / ``Detector``) to hide
the method resolving ``Futures`` from users.
