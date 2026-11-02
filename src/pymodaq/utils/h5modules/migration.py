"""Migration of the h5 files written by older versions of PyMoDAQ

Older versions stored the strings of the string nodes (such as the logger) as pickles. They are still read, but
the migration rewrites them as plain UTF-8, as the current version does, in a copy of the file.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

from pymodaq.utils.safe_pickle import restricted_loads, UnsafePickleError

from pymodaq.utils.h5modules.backends import get_attr


def default_destination(source: Path) -> Path:
    return source.with_name(f'{source.stem}_migrated{source.suffix}')


def migrate_h5_file(source: Union[str, Path], destination: Optional[Union[str, Path]] = None) -> Tuple[Path, int]:
    """Write a copy of a h5 file in which the pickled strings are rewritten as UTF-8

    The source file is never modified, and an existing destination file is never overwritten.

    Parameters
    ----------
    source: str or Path
        The file to migrate
    destination: str or Path
        The file to create, by default the name of the source followed by _migrated

    Returns
    -------
    Path: the migrated file
    int: the number of string nodes that were migrated

    Raises
    ------
    FileExistsError
        if the destination exists
    UnsafePickleError
        if a string node contains anything else than a string, in this case nothing is written
    """
    import h5py

    source = Path(source)
    destination = default_destination(source) if destination is None else Path(destination)
    if destination.exists():
        raise FileExistsError(f'{destination} already exists, it will not be overwritten')
    part = destination.with_name(destination.name + '.part')
    shutil.copyfile(source, part)
    try:
        migrated = 0
        with h5py.File(part, 'r+') as h5file:
            to_migrate = []
            h5file.visititems(lambda name, obj: to_migrate.append(obj) if _is_string_node(obj) else None)
            for dataset in to_migrate:
                migrated += _migrate_string_node(dataset)
        os.replace(part, destination)
    finally:
        if part.exists():
            part.unlink()
    return destination, migrated


def _is_string_node(obj) -> bool:
    import h5py
    if not isinstance(obj, h5py.Dataset):
        return False
    try:
        return get_attr(obj, 'CLASS', 'h5py') == 'VLARRAY' and get_attr(obj, 'subdtype', 'h5py') == 'string'
    except KeyError:
        return False


def _migrate_string_node(dataset) -> int:
    """Rewrite the pickled strings of a node, returns 1 if the node had some, 0 otherwise"""
    new_values = {}
    for index in range(len(dataset)):
        raw = bytes(dataset[index])
        if raw[:1] == b'\x80':
            text = restricted_loads(raw)
            if not isinstance(text, str):
                raise UnsafePickleError(f'Refused to migrate {dataset.name}: it does not contain only strings')
            new_values[index] = text
    for index, text in new_values.items():  # nothing is written if a value above was refused
        dataset[index] = np.frombuffer(text.encode('utf-8'), np.uint8)
    return 1 if new_values else 0
