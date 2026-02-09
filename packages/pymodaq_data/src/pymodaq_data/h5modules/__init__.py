from . import browsing
from .utils import register_exporter, register_exporters
from .backends import backends_available

from pymodaq_utils.config import Config
from pymodaq_utils.logger import set_logger

logger = set_logger('pymodaq_data.h5modules')

register_exporters()


def get_hdf5_backend(config: Config = None) -> str:
    """Get the configured HDF5 backend, falling back to available ones if needed.

    Similar to Qt backend selection, this function:
    1. Gets the wanted backend from config (first element of the list)
    2. Checks if it's available
    3. Falls back to other available backends if needed
    4. Updates the config with the working backend

    Parameters
    ----------
    config : Config, optional
        Config instance. If None, creates a new one.

    Returns
    -------
    str
        The name of the available HDF5 backend to use
    """
    if config is None:
        config = Config()

    # Get configured backends list
    try:
        configured_backends = config('data_saving', 'h5file', 'hdf5_backend')
        if not isinstance(configured_backends, list):
            configured_backends = [configured_backends]
    except Exception:
        # Fallback for old config location
        try:
            configured_backends = config('general', 'hdf5_backend')
            if not isinstance(configured_backends, list):
                configured_backends = [configured_backends]
        except Exception:
            configured_backends = ['tables', 'h5py', 'h5pyd']

    wanted_backend = configured_backends[0]

    # Check if wanted backend is available
    if wanted_backend in backends_available:
        return wanted_backend

    # Try other configured backends
    logger.warning(f"HDF5 backend '{wanted_backend}' is not available. "
                   f"Available backends: {backends_available}")

    for backend in configured_backends[1:]:
        if backend in backends_available:
            logger.info(f"Falling back to HDF5 backend: {backend}")
            # Update config with the working backend
            try:
                config['data_saving', 'h5file', 'hdf5_backend'] = [backend] + [
                    b for b in configured_backends if b != backend
                ]
                config.save()
            except Exception:
                pass  # Config update is nice-to-have, not critical
            return backend

    # Last resort: use first available backend
    if backends_available:
        fallback = backends_available[0]
        logger.warning(f"No configured backend available. Using: {fallback}")
        return fallback

    raise ImportError("No HDF5 backend available. Please install pytables or h5py.")


