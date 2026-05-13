import pytest

from pymodaq_utils.hardware.base import HardwareCache
from pymodaq_utils.hardware import visa, serial_ports, invalidate_all_caches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CountingCache(HardwareCache):
    """Minimal concrete subclass used to test base-class caching logic."""
    _cache = None
    fetch_count = 0

    @classmethod
    def _fetch(cls):
        cls.fetch_count += 1
        return ['resource_a', 'resource_b']

    @classmethod
    def list_resources(cls):
        return list(cls._get_cache())

    @classmethod
    def reset(cls):
        cls._cache = None
        cls.fetch_count = 0


# ---------------------------------------------------------------------------
# HardwareCache base behaviour
# ---------------------------------------------------------------------------

class TestHardwareCacheBase:

    def setup_method(self):
        _CountingCache.reset()

    def test_fetch_called_once(self):
        # Core guarantee: no matter how many times list_resources() is called,
        # the expensive OS-level _fetch() runs exactly once per process lifetime.
        _CountingCache.list_resources()
        _CountingCache.list_resources()
        assert _CountingCache.fetch_count == 1

    def test_returns_correct_data(self):
        assert _CountingCache.list_resources() == ['resource_a', 'resource_b']

    def test_invalidate_triggers_refetch(self):
        # After invalidation the cache is empty, so the next call must
        # re-run _fetch() — this is the hot-plug refresh path.
        _CountingCache.list_resources()
        _CountingCache.invalidate_cache()
        _CountingCache.list_resources()
        assert _CountingCache.fetch_count == 2

    def test_cache_is_none_after_invalidate(self):
        # Validates the internal reset so _get_cache() knows to call _fetch()
        # again on the next access (tested separately in test_invalidate_triggers_refetch).
        _CountingCache.list_resources()
        _CountingCache.invalidate_cache()
        assert _CountingCache._cache is None

    def test_subclasses_have_independent_caches(self):
        # Each subclass stores its result in its own _cache class variable.
        # Invalidating one must not affect the other — otherwise a Newport
        # plugin resetting its cache would silently clear an Arduino plugin's cache.
        class CacheA(HardwareCache):
            _cache = None

            @classmethod
            def _fetch(cls):
                return ['a']

            @classmethod
            def list_resources(cls):
                return list(cls._get_cache())

        class CacheB(HardwareCache):
            _cache = None

            @classmethod
            def _fetch(cls):
                return ['b']

            @classmethod
            def list_resources(cls):
                return list(cls._get_cache())

        assert CacheA.list_resources() == ['a']
        assert CacheB.list_resources() == ['b']
        CacheA.invalidate_cache()
        assert CacheA._cache is None
        assert CacheB._cache is not None  # CacheB untouched


# ---------------------------------------------------------------------------
# visa module
# ---------------------------------------------------------------------------

class TestVisaModule:

    def setup_method(self):
        # Start each test with a clean cache so tests are isolated.
        visa.VisaCache.invalidate_cache()

    def test_list_resources_returns_list(self):
        # Passes even when pyvisa is not installed: the module must never raise.
        assert isinstance(visa.list_resources(), list)

    def test_list_serial_resources_returns_list(self):
        assert isinstance(visa.list_serial_resources(), list)

    def test_list_resource_aliases_returns_list(self):
        assert isinstance(visa.list_resource_aliases(), list)

    def test_serial_resources_are_subset_of_all(self):
        # list_serial_resources() is a filtered view of list_resources();
        # every ASRL entry must also appear in the full resource list.
        # Skipped when pyvisa is absent: an empty list would make this pass
        # vacuously without testing anything.
        pytest.importorskip('pyvisa')
        all_r = visa.list_resources()
        serial_r = visa.list_serial_resources()
        assert all(r in all_r for r in serial_r)

    def test_serial_resources_start_with_asrl(self):
        # VISA serial resources always begin with 'ASRL' by the VISA standard.
        # Skipped when pyvisa is absent for the same reason as above.
        pytest.importorskip('pyvisa')
        for r in visa.list_serial_resources():
            assert r.startswith('ASRL')

    def test_fetch_called_once_across_multiple_functions(self, monkeypatch):
        # Calling list_resources(), list_serial_resources(), and
        # list_resource_aliases() in sequence must trigger only one backend
        # query — the whole point of this module.
        call_count = []
        original_fetch = visa.VisaCache._fetch.__func__

        @classmethod
        def counting_fetch(cls):
            call_count.append(1)
            return original_fetch(cls)

        monkeypatch.setattr(visa.VisaCache, '_fetch', counting_fetch)
        visa.VisaCache.invalidate_cache()

        visa.list_resources()
        visa.list_serial_resources()
        visa.list_resource_aliases()

        assert len(call_count) == 1


# ---------------------------------------------------------------------------
# serial_ports module
# ---------------------------------------------------------------------------

class TestSerialPortsModule:

    def setup_method(self):
        serial_ports.SerialPortsCache.invalidate_cache()

    def test_list_resources_returns_list(self):
        # Passes even when pyserial is not installed.
        assert isinstance(serial_ports.list_resources(), list)

    def test_list_port_descriptions_returns_list(self):
        assert isinstance(serial_ports.list_port_descriptions(), list)

    def test_resources_and_descriptions_same_length(self):
        # Both lists are derived from the same cached port objects, so they
        # must always be parallel (index N in one matches index N in the other).
        assert len(serial_ports.list_resources()) == len(serial_ports.list_port_descriptions())

    def test_fetch_called_once_across_multiple_functions(self, monkeypatch):
        # Same single-fetch guarantee as the visa module.
        call_count = []
        original_fetch = serial_ports.SerialPortsCache._fetch.__func__

        @classmethod
        def counting_fetch(cls):
            call_count.append(1)
            return original_fetch(cls)

        monkeypatch.setattr(serial_ports.SerialPortsCache, '_fetch', counting_fetch)
        serial_ports.SerialPortsCache.invalidate_cache()

        serial_ports.list_resources()
        serial_ports.list_port_descriptions()

        assert len(call_count) == 1


# ---------------------------------------------------------------------------
# Package-level helper
# ---------------------------------------------------------------------------

def test_invalidate_all_caches_clears_both():
    # Populate both caches first so the assertion is meaningful.
    visa.list_resources()
    serial_ports.list_resources()

    invalidate_all_caches()

    assert visa.VisaCache._cache is None
    assert serial_ports.SerialPortsCache._cache is None
