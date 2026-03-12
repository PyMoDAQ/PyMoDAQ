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
without any PyMoDAQ GUI.  The scripting utilities live in
:mod:`pymodaq.scripting`.

Class Hierarchy
~~~~~~~~~~~~~~~~

The scripting layer is built around a two-tier design:

* **Low-level wrappers** (in :mod:`pymodaq.scripting.utils`) manage the LECO
  plumbing – listener, communicator, director, and callbacks.
* **Public device classes** (in :mod:`pymodaq.scripting.devices`) expose a
  clean Python API and hide the ``Future``-resolution callbacks from the user.

The inheritance tree is::

   LECOBaseWrapper
   ├── LECODeviceWrapper          # adds settings management
   │   ├── LECOActuatorWrapper    # move commands & position callbacks
   │   └── LECODetectorWrapper    # snap/grab commands & data callbacks
   └── LECODashboardWrapper       # preset/config/device-list commands

   Device[WrapperT]               # generic public interface
   ├── Actuator                   # wraps LECOActuatorWrapper
   ├── Detector                   # wraps LECODetectorWrapper
   └── Dashboard                  # wraps LECODashboardWrapper


``LECOBaseWrapper``
~~~~~~~~~~~~~~~~~~~~

:class:`~pymodaq.scripting.utils.LECOBaseWrapper` provides all the common LECO
infrastructure for every scripting wrapper:

1. Creates a :class:`pyleco.utils.listener.Listener` registered on the LECO
   network under ``scripting_<device_name>``.
2. Obtains a ``communicator`` from the listener and wraps it in a
   :class:`pyleco.directors.director.Director` pointed at the target Actor.
3. Registers a ``_clean`` shutdown hook via :func:`atexit.register`.

.. code-block:: python

   class LECOBaseWrapper:
       def __init__(self, device_name: str, **kwargs) -> None:
           self._device_name = device_name

           self._listener = Listener(name=self.leco_name, timeout=None)
           self._listener.start_listen()

           self._communicator = self._listener.get_communicator()
           self._director = Director(actor=self.name,
                                     communicator=self._communicator, **kwargs)
           atexit.register(self._clean)

       @cached_property
       def leco_name(self) -> str:
           return f'scripting_{self.name}'

       @cached_property
       def name(self) -> str:
           return self._device_name

       def _clean(self):
           self.sign_out()
           self._listener.close()
           self._director.close()
           self._communicator.close()

       def sign_out(self):
           self._director.ask_rpc('sign_out', actor='COORDINATOR')

       def set_remote_name(self):
           self._director.ask_rpc('set_remote_name', name=self.leco_name)

Key points:

* ``leco_name`` is ``scripting_<name>`` – the name this wrapper registers on
  the LECO network.
* ``set_remote_name()`` must be called before any RPC that expects an
  asynchronous reply, so the Actor knows where to send the answer.
* ``sign_out()`` is public and can be called explicitly; ``_clean()`` is
  called automatically at interpreter exit via :func:`atexit.register`.


``LECODeviceWrapper``
~~~~~~~~~~~~~~~~~~~~~~

:class:`~pymodaq.scripting.utils.LECODeviceWrapper` extends
:class:`~pymodaq.scripting.utils.LECOBaseWrapper` with settings management
shared by actuators and detectors.  In its ``__init__`` it registers two
callbacks on the listener:

* ``set_director_settings`` (plain RPC) – receives the XML settings bytes and
  resolves the ``_settings_future``.
* ``set_director_info`` (binary RPC) – placeholder for device-specific
  information (overridden by subclasses as needed).

.. code-block:: python

   class LECODeviceWrapper(LECOBaseWrapper):
       def __init__(self, device: str, **kwargs) -> None:
           self._base_settings: Optional[Element] = None
           self._settings_future: Optional[Future[Element]] = None

           super().__init__(device, **kwargs)

           self._listener.register_rpc_method(self.set_director_settings)
           self._listener.register_binary_rpc_method(self.set_director_info,
                                                     accept_binary_input=True)

       def get_settings(self) -> Future[Element]:
           future = Future()
           self._settings_future = future
           self.set_remote_name()
           self._director.ask_rpc("get_settings")
           return future

       def set_settings(self, settings: Element):
           # Diffs the modified tree against the original and sends only changes.
           if self._base_settings is not None:
               for (path, modified) in compare_xml_trees(self._base_settings, settings):
                   ...  # serialises and sends each changed parameter
       ...

Writing a New Scripting Wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To expose a new LECO-enabled component via scripting, subclass
:class:`~pymodaq.scripting.utils.LECOBaseWrapper` (or
:class:`~pymodaq.scripting.utils.LECODeviceWrapper` if settings support is
needed) and follow these steps:

1. **Declare ``Future`` attributes** for each asynchronous reply your wrapper
   expects.
2. **Register Director-side callbacks** on ``self._listener`` in ``__init__``.
   Use ``register_rpc_method`` for plain JSON replies and
   ``register_binary_rpc_method`` for binary-serialised PyMoDAQ objects.
3. **Write command methods** that create a ``Future``, call
   ``self.set_remote_name()``, then ``self._director.ask_rpc(<command_name>)``, and
   return the ``Future``.
4. **Write callback methods** that deserialize the reply and resolve the
   matching ``Future``.

Minimal skeleton:

.. code-block:: python

   from concurrent.futures import Future, InvalidStateError
   from serializall import SerializableFactory
   from pymodaq.scripting.utils import LECOBaseWrapper

   sf = SerializableFactory()

   class MyComponentWrapper(LECOBaseWrapper):
       def __init__(self, actor_name: str = "my_component", **kwargs) -> None:
           self._some_result_future: Optional[Future] = None

           super().__init__(actor_name, **kwargs)

           # 2 – register Director-side callbacks
           self._listener.register_rpc_method(self.something_done)
           # for binary replies:
           # self._listener.register_binary_rpc_method(self.some_data,
           #                                           accept_binary_input=True)

       # 3 – command methods

       def do_something(self, value: str) -> Future[str]:
           future = Future()
           self._some_result_future = future
           self.set_remote_name()
           # value should be serialized using serializall for complex values
           self._director.ask_rpc("do_something", value=value)
           return future

       # 4 – callback methods

       def something_done(self, result: str) -> None:
           try:
               self._some_result_future.set_result(result)
               self._some_result_future = None
           except (InvalidStateError, AttributeError):
               pass

Binary replies (e.g. a ``DataToExport``) require ``register_binary_rpc_method``
and deserialization:

.. code-block:: python

   # in __init__:
   self._listener.register_binary_rpc_method(self.set_data, accept_binary_input=True)

   # callback:
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
       self.set_remote_name()
       self._director.ask_rpc(
           "move_abs",
           position=None,
           additional_payload=[sf.get_apply_serializer(value)],
       )
       return future


The ``Device`` Public Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

End-user scripts should not deal with the low-level wrappers directly.
Instead, a :class:`~pymodaq.scripting.utils.Device` subclass wraps a wrapper
and exposes only the user-facing methods, hiding the ``Future``-resolution
callbacks:

.. code-block:: python

   from abc import ABC
   from typing import Generic, TypeVar
   from pymodaq.scripting.utils import LECOBaseWrapper

   WrapperT = TypeVar('WrapperT', bound=LECOBaseWrapper)

   class Device(ABC, Generic[WrapperT]):
       def __init__(self, wrapper: WrapperT) -> None:
           self._wrapper = wrapper

       @property
       def leco_name(self): return self._wrapper.leco_name

       @property
       def name(self) -> str: return self._wrapper.name

       def sign_out(self) -> None: self._wrapper.sign_out()

   class MyComponent(Device[MyComponentWrapper]):
       def __init__(self, actor_name: str = "my_component", **kwargs) -> None:
           super().__init__(MyComponentWrapper(actor_name, **kwargs))

       def do_something(self, value: str) -> Future[str]:
           return self._wrapper.do_something(value)

The existing :class:`~pymodaq.scripting.devices.Actuator`,
:class:`~pymodaq.scripting.devices.Detector`, and
:class:`~pymodaq.scripting.devices.Dashboard` classes in
:mod:`pymodaq.scripting.devices` follow exactly this pattern.


Using the Public Classes in a Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the public classes in place, scripts are straightforward.  Calling
``.result()`` on a ``Future`` blocks until the Actor replies:

.. code-block:: python

   from pymodaq.scripting import Actuator, Detector, Dashboard

   # connect to a running Dashboard and load a preset
   dashboard = Dashboard()
   dashboard.apply_preset('default').result()

   # get all loaded modules as Actuator / Detector instances
   devices = dashboard.get_scripting_devices()
   theta  = devices['actuators']['Angle']
   camera = devices['detectors']['Camera']

   # blocking move, then snap
   pos   = theta.move_abs('90°').result()
   frame = camera.snap().result()

``get_scripting_devices()`` calls ``get_devices()`` on the Dashboard and
automatically wraps the returned names in :class:`~pymodaq.scripting.devices.Actuator`
and :class:`~pymodaq.scripting.devices.Detector` instances, so the caller
never has to manage LECO names manually.
