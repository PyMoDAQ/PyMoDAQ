# -*- coding: utf-8 -*-
"""Utilities for reading HDF5 files written with SWMR (Single Writer Multiple Reader) mode.

Typical usage
-------------
Open the file once, collect dataset references, then poll in a loop:

    from pymodaq_data.h5modules import open_h5_file_for_reading
    from pymodaq_data.h5modules.swmr import collect_datasets, refresh_cached

    f, is_swmr = open_h5_file_for_reading("scan.h5")
    cache = collect_datasets(f["RawData"])   # dict[str, h5py.Dataset]

    while acquiring:
        refresh_cached(cache)
        data = cache["/RawData/CH000/Data0D/Data00/data"][:]
"""

from __future__ import annotations

from typing import Dict

import h5py


def collect_datasets(group: h5py.Group) -> Dict[str, h5py.Dataset]:
    """Walk *group* recursively and return a mapping of absolute path → dataset.

    The returned dict can be passed to :func:`refresh_cached` on every poll
    cycle instead of re-walking the tree each time.

    Parameters
    ----------
    group:
        Any ``h5py.Group`` (or ``h5py.File``, which is also a group).

    Returns
    -------
    dict
        ``{"/absolute/path": h5py.Dataset, ...}`` for every dataset found
        under *group*.

    Examples
    --------
    >>> f, _ = open_h5_file_for_reading("scan.h5")
    >>> cache = collect_datasets(f["RawData"])
    >>> cache.keys()
    dict_keys(['/RawData/CH000/Data0D/Data00/data', ...])
    """
    datasets: Dict[str, h5py.Dataset] = {}

    def _visitor(name: str, obj: h5py.HLObject) -> None:
        if isinstance(obj, h5py.Dataset):
            # name is relative; build the absolute path from the group's name
            prefix = group.name.rstrip("/")
            datasets[f"{prefix}/{name}"] = obj

    group.visititems(_visitor)
    return datasets


def refresh_datasets(group: h5py.Group) -> None:
    """Refresh every dataset under *group* so that SWMR readers see the
    latest data written by the writer process.

    This is a convenience wrapper for one-shot use.  For polling loops prefer
    :func:`collect_datasets` + :func:`refresh_cached` to avoid re-walking the
    tree on every iteration.

    Parameters
    ----------
    group:
        Any ``h5py.Group`` (or ``h5py.File``).

    Notes
    -----
    ``refresh()`` is a metadata/chunk-index call; it does **not** read the
    actual data.  The data is only transferred when you access dataset
    elements (``ds[:]``, ``ds[-1]``, etc.).
    """
    def _visitor(name: str, obj: h5py.HLObject) -> None:
        if isinstance(obj, h5py.Dataset):
            obj.id.refresh()

    group.visititems(_visitor)


def refresh_cached(cache: Dict[str, h5py.Dataset]) -> None:
    """Refresh every dataset in a pre-built cache dict.

    This is the fast path for polling loops: call :func:`collect_datasets`
    once to build *cache*, then call this function on each iteration.

    Parameters
    ----------
    cache:
        A ``{path: h5py.Dataset}`` dict as returned by
        :func:`collect_datasets`.

    Examples
    --------
    >>> cache = collect_datasets(f["RawData"])
    >>> while acquiring:
    ...     refresh_cached(cache)
    ...     latest_row = cache["/RawData/CH000/Data0D/Data00/data"][-1]
    """
    for ds in cache.values():
        ds.id.refresh()
