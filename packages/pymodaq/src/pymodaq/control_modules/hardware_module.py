"""Shared base for HardwareThread-backed control modules (DAQ_Move, DAQ_Viewer).

HardwareModule provides the common lifecycle:
- attach to / detach from HardwareThread via HardwareRegistry
- relay hw_settings changes bidirectionally (GUI ↔ plugin thread)
- common slots: _on_hardware_status, _relay_hw_settings_change, _on_hw_settings_changed

Module-specific signals (write-request for actuators, start-grab for detectors)
and data-handling slots remain in the concrete subclasses.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from qtpy.QtCore import Signal, Slot, QSignalBlocker, QMetaObject, Qt

from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.utils import ParameterControlModule
from pymodaq.control_modules.hardware_registry import HardwareRegistry, HardwareKey
from pymodaq.control_modules.subscription import Subscription

if TYPE_CHECKING:
    from pymodaq.control_modules.hardware_thread import HardwareThread
    from pymodaq_gui.parameter import Parameter

__all__ = ['HardwareModule']


class HardwareModule(ParameterControlModule):
    """Intermediate base class for HardwareThread-backed control modules.

    Provides attach/detach lifecycle, bidirectional hw_settings relay, and
    common slots.  Concrete subclasses add their own signals and data handlers.

    Subclasses must implement:
        _get_plugin_class()          → the plugin class for the selected instrument
        _connect_ct_signals(ct)      → connect module-specific CT signals
        _disconnect_ct_signals(ct)   → disconnect them

    Subclasses may override:
        _PER_CHANNEL_PARAMS          → frozenset of param names that are per-channel
        _derive_channel()            → return the channel name (default: '')
        _on_hardware_connected()     → called when hardware_status(True) fires
        _on_per_channel_param_changed(path, data) → e.g. update units suffix in UI
    """

    # Per-channel parameter identifiers: either a top-level name string (e.g.
    # 'units') or a full path tuple (e.g. ('controller', 'axis')).  Params that
    # match are kept in each module's LOCAL settings and are never mirrored to
    # the shared _hw_settings.
    _PER_CHANNEL_PARAMS: frozenset = frozenset()

    def _is_per_channel(self, path: list) -> bool:
        """Return True if *path* identifies a per-channel (per-module) parameter.

        Supports both top-level name strings and full path tuples so that
        nested params like ('controller', 'axis') can be flagged without
        making the entire 'controller' group per-channel.
        """
        if not path:
            return False
        return (path[0] in self._PER_CHANNEL_PARAMS
                or tuple(path) in self._PER_CHANNEL_PARAMS)

    # Signals that cross from the GUI thread into the hardware thread.
    _unsubscribe_request = Signal(object)           # (Subscription,) → ct.unsubscribe
    _settings_update   = Signal(list, object, str)  # (path, data, change) → ct.update_settings

    _subscribe_request = Signal(object)             # (Subscription,) → ct.subscribe

    def __init__(self, **kwargs):
        # Set CT attributes before ParameterControlModule (and its ParameterManager
        # parent) runs.  Parameter-tree change callbacks fire during that
        # construction and invoke _module_value_changed which reads self._ct.
        self._ct: Optional[HardwareThread] = None
        self._ct_key: Optional[HardwareKey] = None
        self._channel: str = ''
        self._hw_settings: Optional[Parameter] = None
        self._syncing_from_hw: bool = False
        self._init_failed: bool = False  # set True on hardware_status(False) for fast poll_init exit
        self._initialized_state: bool = False
        super().__init__(**kwargs)

    @property
    def initialized_state(self) -> bool:
        """bool: Check if the module is initialized (CT-based; overrides the
        legacy ControlModule property, which reads _controller_and_thread)."""
        return self._initialized_state

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _hw(self, *path):
        """Read a value from the shared hw_settings, falling back to local settings."""
        hw = getattr(self, '_hw_settings', None)
        if hw is not None:
            return hw[path]
        return self.settings[(self._hw_settings_name, *path)]

    def _hw_child(self, *path):
        """Return a Parameter node from hw_settings, falling back to local settings."""
        hw = getattr(self, '_hw_settings', None)
        if hw is not None:
            return hw.child(*path)
        return self.settings.child(self._hw_settings_name, *path)

    # ── Hooks (override in subclasses) ────────────────────────────────────────

    def _get_plugin_class(self) -> type:
        raise NotImplementedError

    def _derive_channel(self) -> str:
        """Return the channel name for this module ('' = broadcast/single-axis)."""
        return ''

    def _connect_ct_signals(self, ct: 'HardwareThread') -> None:
        """Connect module-specific CT signals after attach."""
        pass

    def _disconnect_ct_signals(self, ct: 'HardwareThread') -> None:
        """Disconnect module-specific CT signals before detach."""
        pass

    def _on_hardware_connected(self) -> None:
        """Called when hardware_status(True) fires; e.g. trigger initial read."""
        pass

    def _on_per_channel_param_changed(self, path: list, data) -> None:
        """Called after a per-channel param is written to local settings."""
        pass

    def _dispatch_command_hardware(self, command: ThreadCommand) -> None:
        """Handle a legacy ``command_hardware`` ThreadCommand.

        ``command_hardware`` predates the HardwareThread architecture and
        was historically wired to a per-module hardware-thread worker's
        ``queue_command``.  External callers (e.g. ``ModulesManager``, used
        by ``DAQ_Scan`` and other extensions) still emit commands on this
        signal to trigger grabs/moves.  Override in subclasses to translate
        those commands onto the CT-based public API (``grab_data``,
        ``move_abs``, ...).
        """
        pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def init_hardware(self, do_init=True):
        """Attach to (or detach from) the shared HardwareThread."""
        if not do_init:
            self._detach_controller()
            return
        self._init_failed = False
        try:
            plugin_class = self._get_plugin_class()
            hw_cls = getattr(plugin_class, 'hardware_class', plugin_class)
            key = HardwareKey(
                hardware_class=hw_cls,
                controller_id=self.settings[self._hw_settings_name, 'controller', 'controller_ID'],
            )
            params_state = self.settings.child(self._hw_settings_name).saveState()
            ctrl = HardwareRegistry.get().attach(
                key, plugin_class, params_state=params_state,
            )
            ct = ctrl.thread
            hw_settings = ctrl.settings
            self._ct = ct
            self._ct_key = key
            # Derive channel from LOCAL settings before assigning _hw_settings.
            # axis_name uses _hw_child which falls back to local settings when
            # _hw_settings is None.  If we assign _hw_settings first, all
            # subscribers on the same CT read the same shared axis value and
            # end up with identical _channel (e.g. both 'X' instead of 'X' and
            # 'Theta').
            self._channel = self._derive_channel()
            self._hw_settings = hw_settings

            ct.hardware_status.connect(self._on_hardware_status)
            ct.settings_changed.connect(self._on_hw_settings_changed)

            self.command_hardware[ThreadCommand].connect(self._dispatch_command_hardware)

            self._unsubscribe_request.connect(ct.unsubscribe)
            self._settings_update.connect(ct.update_settings)

            self._subscribe_request.connect(ct.subscribe)

            self._connect_ct_signals(ct)
            self.connect_leco(True)

            # Queued so that settings_changed emissions from ini (e.g. units) arrive
            # after the connections above.  ini_hardware is idempotent in the device
            # thread, so every subscriber can request it and only the first one initialises.
            QMetaObject.invokeMethod(ct, 'ini_hardware',
                                     Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            self.logger.exception(str(e))

    def _detach_controller(self):
        """Disconnect signals and release the registry reference."""
        self._pre_close_hardware()
        self.connect_leco(False)
        # Restore the per-module settings action before releasing the key.
        if self.ui is not None and hasattr(self.ui, 'release_shared_settings_action'):
            self.ui.release_shared_settings_action()
        if self._ct is not None:
            try:
                self._disconnect_ct_signals(self._ct)
                self._ct.hardware_status.disconnect(self._on_hardware_status)
                self._ct.settings_changed.disconnect(self._on_hw_settings_changed)
                self.command_hardware[ThreadCommand].disconnect(self._dispatch_command_hardware)
                self._unsubscribe_request.disconnect(self._ct.unsubscribe)
                self._settings_update.disconnect(self._ct.update_settings)
                self._subscribe_request.disconnect(self._ct.subscribe)
            except Exception:
                pass
            self._ct = None
        if self._hw_settings is not None:
            self._hw_settings = None
        if self._ct_key is not None:
            HardwareRegistry.get().detach(self._ct_key)
            self._ct_key = None
        self._initialized_state = False
        self.init_signal.emit(False)

    def read_channel(self, channel: str, **kwargs) -> Subscription:
        """Read *channel* once; the reading arrives on the returned one-shot subscription."""
        return self.subscribe_channel(channel, None, **kwargs)

    def subscribe_channel(self, channel: str, period_ms: float | None, **kwargs) -> Subscription:
        """Subscribe to periodic readings of *channel*; the returned subscription is owned by the caller.

        Extra keyword arguments (``transform``, ``policy``) are passed to :class:`Subscription`.
        Call :meth:`unsubscribe_channel` to stop; the subscription is deleted once released.
        """
        sub = Subscription(channel, period_ms, parent=self, **kwargs)
        self._subscribe_request.emit(sub)
        return sub

    def unsubscribe_channel(self, sub: Subscription) -> None:
        self._unsubscribe_request.emit(sub)

    # ── Common CT slots ───────────────────────────────────────────────────────

    @Slot(bool, str)
    def _on_hardware_status(self, connected: bool, info: str):
        """Receive hardware connection status from HardwareThread."""
        self.update_status(f'Hardware initialized: {connected}  info: {info}')
        if connected and self._initialized_state:
            # Repeated confirmation, sent to every subscriber when another one attaches.
            return
        self._initialized_state = connected
        if not connected:
            self._init_failed = True  # lets poll_init exit immediately on failure
        if self.ui is not None:
            setattr(self.ui, self._ui_init_attr, connected)
        if connected:
            self._on_hardware_connected()
        self.init_signal.emit(connected)

    @Slot(object, object)
    def _relay_hw_settings_change(self, param, changes):
        """Forward hw_settings edits (from any subscriber) to the hardware thread."""
        if self._ct is None:
            return
        for p, change, data in changes:
            path = self._hw_settings.childPath(p)
            if path is not None:
                self._settings_update.emit(path, data, change)

    def _map_to_module_path(self, path: list) -> list:
        """Normalise a plugin-emitted param path to the module's local layout.

        Base implementation is an identity — subclasses override when their
        plugin may emit flat paths that need regrouping (e.g. DAQ_Move maps
        ``['units']`` → ``['axis_settings', 'units']``).
        """
        return list(path)

    @Slot(str, list, object, str)
    def _on_hw_settings_changed(self, channel: str, path: list, data, change: str):
        """Receive plugin-initiated settings changes and apply them selectively.

        Per-channel parameters (in _PER_CHANNEL_PARAMS) are written to this
        module's local settings under the ``axis_settings`` group, filtered
        by channel.  Old-style plugins emit flat paths (e.g. ``['units']``);
        ``_map_to_module_path`` normalises these to the grouped layout before
        writing.  Per-controller params are written to the shared _hw_settings.
        """
        if change != 'value' or not path:
            return

        mapped = self._map_to_module_path(path)

        if self._is_per_channel(mapped):
            if channel and channel != self._channel:
                return
            self._syncing_from_hw = True
            try:
                self.settings.child(self._hw_settings_name, *mapped).setValue(data)
            except Exception:
                pass
            finally:
                self._syncing_from_hw = False
            self._on_per_channel_param_changed(mapped, data)
            return

        if self._hw_settings is None:
            return
        with QSignalBlocker(self._hw_settings):
            try:
                self._hw_settings.child(*path).setValue(data)
            except Exception:
                pass
        # Mirror into local display so the module's own settings widget stays
        # in sync when another subscriber (or the plugin itself) changed a value.
        self._syncing_from_hw = True
        try:
            self.settings.child(self._hw_settings_name, *path).setValue(data)
        except Exception:
            pass
        finally:
            self._syncing_from_hw = False

    def _module_value_changed(self, param: 'Parameter'):
        """Forward hw_settings edits from this module to the hardware thread.

        Per-controller params are also mirrored to the shared _hw_settings so
        other subscribers (e.g. another axis on the same controller) stay in sync.
        Per-channel params (in _PER_CHANNEL_PARAMS) are not mirrored.
        """
        if getattr(self, '_syncing_from_hw', False):
            return
        if self._ct is not None:
            hw_subtree = self.settings.child(self._hw_settings_name)
            hw_path = hw_subtree.childPath(param)
            if hw_path is not None:
                self._settings_update.emit(hw_path, param.value(), 'value')
                if self._hw_settings is not None and not self._is_per_channel(hw_path):
                    with QSignalBlocker(self._hw_settings):
                        try:
                            self._hw_settings.child(*hw_path).setValue(param.value())
                        except Exception:
                            pass
