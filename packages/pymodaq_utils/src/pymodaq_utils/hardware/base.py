
class HardwareCache:
    """Base class for process-lifetime hardware discovery caches.

    Each subclass calls its backend (pyvisa, pyserial, …) exactly once per
    process. The result is stored as a class variable and reused by every
    caller, regardless of which plugin package triggered the first call.

    Subclasses must override :meth:`_fetch` and :meth:`list_resources`.
    Call :meth:`invalidate_cache` to force re-discovery, for example after
    hot-plugging a device.

    Example — defining a new backend::

        class MyCache(HardwareCache):
            _cache = None

            @classmethod
            def _fetch(cls):
                return some_expensive_os_call()

            @classmethod
            def list_resources(cls) -> list[str]:
                return [item.id for item in cls._get_cache()]
    """

    _cache = None

    @classmethod
    def _fetch(cls):
        """Perform the actual hardware discovery.

        Called at most once per process. Must return a value that can be
        stored and reused (list, dict, …). Should catch all exceptions and
        return an empty container so that callers never need to guard against
        missing backends.
        """
        raise NotImplementedError

    @classmethod
    def _get_cache(cls):
        """Return the cached discovery result, populating it on first call."""
        if cls._cache is None:
            cls._cache = cls._fetch()
        return cls._cache

    @classmethod
    def invalidate_cache(cls) -> None:
        """Clear the cache so the next call to any list_* method re-discovers.

        Use this after hot-plugging a device or when the set of available
        instruments may have changed since process startup.
        """
        cls._cache = None

    @classmethod
    def list_resources(cls) -> list[str]:
        """Return a list of connectable resource strings for this backend."""
        raise NotImplementedError
