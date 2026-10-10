"""Tests for HardwareRegistry: one hardware thread per device, shared by its subscribers."""
from __future__ import annotations

import subprocess
import sys
import textwrap
import threading

import pytest

from pymodaq.control_modules import hardware_registry
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry
from pymodaq.control_modules.hardware_thread import HardwareThread


class FakeThread(HardwareThread):
    """A HardwareThread that runs no QThread and records close_hardware."""

    def __init__(self, plugin_class, params_state=None):
        super().__init__(plugin_class, params_state)
        self.close_hardware_called = False

    def close_hardware(self):
        self.close_hardware_called = True


class FakeRegistry(HardwareRegistry):
    def _make_thread(self, plugin_class, params_state):
        return FakeThread(plugin_class, params_state)


class PluginA:
    params: list = []


class PluginB:
    params: list = []


def key_for(hardware_class=PluginA, controller_id=0):
    return HardwareKey(hardware_class=hardware_class, controller_id=controller_id)


class TestHardwareKey:

    def test_equal_for_same_class_and_id(self):
        assert key_for() == key_for()

    def test_different_controller_id_is_different(self):
        assert key_for(controller_id=1) != key_for(controller_id=2)

    def test_different_hardware_class_is_different(self):
        assert key_for(PluginA) != key_for(PluginB)

    def test_usable_as_dict_key(self):
        assert {key_for(): 'x'}[key_for()] == 'x'

    def test_immutable(self):
        with pytest.raises(Exception):
            key_for().controller_id = 5


class TestAttachDetach:

    def test_first_attach_creates_thread_and_settings(self):
        registry = FakeRegistry()
        ctrl = registry.attach(key_for(), PluginA)
        thread, settings = ctrl.thread, ctrl.settings
        assert isinstance(thread, FakeThread)
        assert settings is not None
        assert registry.ref_count(key_for()) == 1

    def test_second_attach_shares_thread_and_settings(self):
        registry = FakeRegistry()
        first = registry.attach(key_for(), PluginA)
        second = registry.attach(key_for(), PluginA)
        assert first is second
        assert registry.ref_count(key_for()) == 2

    def test_different_controller_ids_get_different_threads(self):
        registry = FakeRegistry()
        a = registry.attach(key_for(controller_id=1), PluginA)
        b = registry.attach(key_for(controller_id=2), PluginA)
        assert a.thread is not b.thread

    def test_attach_with_another_plugin_class_is_refused(self):
        registry = FakeRegistry()
        registry.attach(key_for(), PluginA)
        with pytest.raises(ValueError, match='already attached'):
            registry.attach(key_for(), PluginB)

    def test_detach_decrements_then_last_one_stops_the_thread(self):
        registry = FakeRegistry()
        ctrl = registry.attach(key_for(), PluginA)
        thread, _ = ctrl.thread, ctrl.settings
        registry.attach(key_for(), PluginA)
        registry.detach(key_for())
        assert registry.is_known(key_for())
        assert not thread.close_hardware_called
        registry.detach(key_for())
        assert not registry.is_known(key_for())
        assert thread.close_hardware_called

    def test_detach_unknown_key_is_a_noop(self):
        registry = FakeRegistry()
        registry.detach(key_for())
        assert registry.ref_count(key_for()) == 0

    def test_reattach_after_full_release_creates_a_new_thread(self):
        registry = FakeRegistry()
        ctrl = registry.attach(key_for(), PluginA)
        first, _ = ctrl.thread, ctrl.settings
        registry.detach(key_for())
        ctrl = registry.attach(key_for(), PluginA)
        second, _ = ctrl.thread, ctrl.settings
        assert second is not first

    def test_params_state_is_used_by_the_first_attach_only(self, monkeypatch):
        registry = FakeRegistry()
        seen = []
        monkeypatch.setattr(hardware_registry, 'make_plugin_settings',
                            lambda plugin_class, params_state: seen.append(params_state) or object())
        registry.attach(key_for(), PluginA, params_state={'first': True})
        registry.attach(key_for(), PluginA, params_state={'second': True})
        assert seen == [{'first': True}]


class TestCloseAll:

    def test_close_all_stops_every_thread_and_clears_entries(self):
        registry = FakeRegistry()
        ctrl = registry.attach(key_for(controller_id=1), PluginA)
        a, _ = ctrl.thread, ctrl.settings
        ctrl = registry.attach(key_for(controller_id=2), PluginA)
        b, _ = ctrl.thread, ctrl.settings
        registry.close_all()
        assert a.close_hardware_called and b.close_hardware_called
        assert not registry.is_known(key_for(controller_id=1))
        assert not registry.is_known(key_for(controller_id=2))

    def test_close_all_on_empty_registry_is_a_noop(self):
        FakeRegistry().close_all()


class TestSingleton:

    def setup_method(self):
        HardwareRegistry._reset_global()

    def teardown_method(self):
        if HardwareRegistry._global is not None:
            HardwareRegistry._global.close_all()
        HardwareRegistry._reset_global()

    def test_get_returns_the_same_instance(self):
        assert HardwareRegistry.get() is HardwareRegistry.get()

    def test_reset_creates_a_fresh_instance(self):
        first = HardwareRegistry.get()
        HardwareRegistry._reset_global()
        assert HardwareRegistry.get() is not first


class TestTeardownOnHardwareThread:

    def test_close_runs_on_device_thread_and_thread_stops(self, qapp):
        import qtpy.QtCore as QtCore
        from qtpy.QtWidgets import QApplication

        closed_on = []

        class _Plugin:
            params: list = []

            def open(self, settings):
                pass

            def close(self):
                closed_on.append(QtCore.QThread.currentThread())

            def read(self, names=None, fresh=True):
                return None

            def write(self, name, value):
                pass

        registry = HardwareRegistry()
        key = key_for(hardware_class=_Plugin)
        ctrl = registry.attach(key, _Plugin)
        thread_obj, _ = ctrl.thread, ctrl.settings
        qt_thread = thread_obj.parent_qt_thread
        QtCore.QMetaObject.invokeMethod(
            thread_obj, 'ini_hardware', QtCore.Qt.ConnectionType.BlockingQueuedConnection)

        registry.detach(key)

        assert len(closed_on) == 1
        assert closed_on[0] != QApplication.instance().thread()
        assert not qt_thread.isRunning()


class TestStoppingThreads:

    def test_a_stalled_thread_is_waited_for_unconditionally_not_abandoned(self, qapp):
        """A 2 s wait timing out must never make detach() return while the thread might still be
        running - that used to be handled by stashing a reference "to keep it alive", but that
        reference died with the registry the moment its caller dropped it, same problem one step
        removed (this is the real fix for the cross-process crash logged in
        device_module_status.md). detach() must instead fall back to an unconditional wait."""
        import qtpy.QtCore as QtCore

        class _Plugin:
            params: list = []

            def open(self, settings):
                pass

            def close(self):
                pass

            def read(self, names=None, fresh=True):
                return None

            def write(self, name, value):
                pass

        registry = HardwareRegistry()
        key = key_for(hardware_class=_Plugin, controller_id=2)
        ctrl = registry.attach(key, _Plugin)
        thread_obj, _ = ctrl.thread, ctrl.settings
        qt_thread = thread_obj.parent_qt_thread
        QtCore.QMetaObject.invokeMethod(
            thread_obj, 'ini_hardware', QtCore.Qt.ConnectionType.BlockingQueuedConnection)

        real_wait = type(qt_thread).wait
        calls = []

        def fake_wait(*args):
            calls.append(args)
            if args:
                return False  # the bounded 2000 ms call "times out"
            return real_wait(qt_thread)  # the unconditional fallback call waits for real - no
            # dangling QThread left behind once this test ends, unlike the mock it replaces.

        qt_thread.wait = fake_wait
        registry.detach(key)
        del qt_thread.wait

        assert calls == [(2000,), ()]  # bounded wait tried first, then an unconditional one - never abandoned
        assert not qt_thread.isRunning()


class TestShutdownHook:

    def test_application_quit_closes_devices(self, qapp):
        import qtpy.QtCore as QtCore

        closed = []

        class _Plugin:
            params: list = []

            def open(self, settings):
                pass

            def close(self):
                closed.append(True)

            def read(self, names=None, fresh=True):
                return None

            def write(self, name, value):
                pass

        HardwareRegistry._reset_global()
        registry = HardwareRegistry.get()
        key = key_for(hardware_class=_Plugin, controller_id=3)
        ctrl = registry.attach(key, _Plugin)
        thread_obj, _ = ctrl.thread, ctrl.settings
        QtCore.QMetaObject.invokeMethod(
            thread_obj, 'ini_hardware', QtCore.Qt.ConnectionType.BlockingQueuedConnection)

        qapp.aboutToQuit.emit()

        assert closed == [True]
        assert not registry.is_known(key)
        HardwareRegistry._reset_global()


class TestDetachDoesNotHoldRegistryLock:

    def test_plugin_close_may_query_registry(self):
        """Runs in a subprocess so that a regression fails by timeout instead of hanging the test run."""
        code = textwrap.dedent("""
            from qtpy.QtCore import QCoreApplication, QMetaObject, Qt
            from pymodaq.control_modules.hardware_registry import HardwareRegistry, HardwareKey

            app = QCoreApplication([])

            class Plugin:
                params = []
                queried = []

                def open(self, settings):
                    pass

                def close(self):
                    Plugin.queried.append(registry.ref_count(key))

                def read(self, names=None, fresh=True):
                    return None

                def write(self, name, value):
                    pass

            registry = HardwareRegistry()
            key = HardwareKey(hardware_class=Plugin, controller_id=4)
            ctrl = registry.attach(key, Plugin)
            thread_obj, _ = ctrl.thread, ctrl.settings
            QMetaObject.invokeMethod(thread_obj, 'ini_hardware', Qt.ConnectionType.BlockingQueuedConnection)
            registry.detach(key)
            print(Plugin.queried)
        """)
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == '[0]'
