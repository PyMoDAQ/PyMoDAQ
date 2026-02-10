from . import browsing
from .utils import register_exporter, register_exporters
from .backends import backends_available
from .swmr import collect_datasets, refresh_datasets, refresh_cached

from pymodaq_data.config import Config
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
        configured_backends = config('general', 'hdf5_backend')
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
                config['general', 'hdf5_backend'] = [backend] + [
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


def open_h5_file_for_reading(filepath, swmr='auto', locking=None):
    """Open an HDF5 file for reading, automatically handling SWMR mode.

    This utility function handles the complexity of opening HDF5 files that may
    or may not be currently being written with SWMR mode.

    Parameters
    ----------
    filepath : str or Path
        Path to the HDF5 file
    swmr : bool or 'auto', optional
        - 'auto' (default): Try to detect if SWMR is needed
        - True: Force SWMR reader mode
        - False: Open normally without SWMR
    locking : bool or None, optional
        File locking mode. None uses h5py default.
        Set to False on Windows if you get locking errors.

    Returns
    -------
    tuple
        (h5py.File, is_swmr_active) - The file handle and whether SWMR is active

    Examples
    --------
    >>> # Open a file being written by PyMoDAQ scan
    >>> f, is_swmr = open_h5_file_for_reading("scan_data.h5")
    >>> if is_swmr:
    ...     ds = f['path/to/data']
    ...     ds.id.refresh()  # Call refresh to see latest data
    >>> f.close()
    """
    import h5py
    from pathlib import Path

    filepath = str(Path(filepath))

    # Build kwargs for h5py.File
    kwargs = {}
    if locking is not None:
        kwargs['locking'] = locking

    if swmr is True:
        # Force SWMR mode
        try:
            f = h5py.File(filepath, 'r', swmr=True, **kwargs)
            return f, True
        except OSError as e:
            # File might not be SWMR-compatible or is locked
            logger.warning(f"Could not open with SWMR: {e}")
            raise

    elif swmr is False:
        # Force non-SWMR mode
        f = h5py.File(filepath, 'r', **kwargs)
        return f, False

    else:  # swmr == 'auto'
        # First try to open without SWMR to check the attribute
        try:
            f = h5py.File(filepath, 'r', **kwargs)
            # Check if file is being written with SWMR
            swmr_active = f.attrs.get('swmr_active', False)
            if swmr_active:
                f.close()
                # Reopen with SWMR
                f = h5py.File(filepath, 'r', swmr=True, **kwargs)
                return f, True
            return f, False
        except OSError as e:
            # File might be locked by SWMR writer, try opening with SWMR
            if 'lock' in str(e).lower() or 'errno = 0' in str(e).lower():
                logger.info("File appears locked, trying SWMR reader mode...")
                try:
                    # On Windows, might need locking=False
                    if locking is None:
                        kwargs['locking'] = False
                    f = h5py.File(filepath, 'r', swmr=True, **kwargs)
                    return f, True
                except OSError:
                    pass
            raise


def is_file_swmr_active(filepath):
    """Check if an HDF5 file is currently being written with SWMR mode.

    Parameters
    ----------
    filepath : str or Path
        Path to the HDF5 file

    Returns
    -------
    bool
        True if the file has swmr_active=True attribute, False otherwise
    """
    import h5py
    from pathlib import Path

    filepath = str(Path(filepath))

    try:
        # Try opening with locking=False to avoid conflicts on Windows
        with h5py.File(filepath, 'r', locking=False) as f:
            return bool(f.attrs.get('swmr_active', False))
    except OSError:
        # If we can't open it, assume SWMR might be active
        return True


