from typing import Any, Dict
import threading


class Singleton(type):
    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Double-checked locking pattern
        # Check first to return early if Singleton exists
        # Then lock and check again as the "real" check
        # should be after locking.
        if cls not in Singleton._instances:
            with Singleton._lock:
                if cls not in Singleton._instances:
                    Singleton._instances[cls] = super().__call__(*args, **kwargs)
        return Singleton._instances[cls]

    @classmethod
    def unregister(cls, target: type):
        with Singleton._lock:
            if target in Singleton._instances:
                del Singleton._instances[target]