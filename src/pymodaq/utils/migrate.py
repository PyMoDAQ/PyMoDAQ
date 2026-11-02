"""The pymodaq_migrate command: migrate the files written by older versions of PyMoDAQ

Older versions stored some data as pickles (the strings of h5 files and the dock layouts). They are still
read, but the files can be migrated to the current formats, in a copy: the original files are not modified.
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from pymodaq.utils.safe_pickle import UnsafePickleError

H5_SUFFIXES = ('.h5', '.hdf5', '.hdf')
LAYOUT_SUFFIXES = ('.dock',)


def migrate_file(source: Path, destination: Optional[Path] = None) -> str:
    """Migrate one file, returns the message to show to the user"""
    suffix = source.suffix.lower()
    if suffix in H5_SUFFIXES:
        from pymodaq.utils.h5modules.migration import migrate_h5_file
        migrated, nodes = migrate_h5_file(source, destination)
        return f'{source}: {nodes} string node(s) migrated, written in {migrated}'
    elif suffix in LAYOUT_SUFFIXES:
        from pymodaq.utils.gui_utils.layout import migrate_layout_file
        migrated = migrate_layout_file(source, destination)
        return f'{source}: layout migrated, written in {migrated}'
    raise ValueError(f'{source}: only {", ".join(H5_SUFFIXES + LAYOUT_SUFFIXES)} files can be migrated')


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog='pymodaq_migrate',
        description='Write a copy of files written by older versions of PyMoDAQ in the current formats '
                    '(the original files are not modified).')
    parser.add_argument('files', nargs='+', type=Path, help='the .h5 and .dock files to migrate')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='the file to write (only when migrating one file), by default the name of the '
                             'file followed by _migrated')
    args = parser.parse_args(argv)
    if args.output is not None and len(args.files) != 1:
        print('--output can only be used with one file', file=sys.stderr)
        return 2

    status = 0
    for source in args.files:
        try:
            if not source.is_file():
                raise FileNotFoundError(f'{source}: no such file')
            print(migrate_file(source, args.output))
        except UnsafePickleError as e:
            print(f'{source}: refused, the file does not contain only plain data ({e})', file=sys.stderr)
            status = 1
        except (OSError, ValueError, ImportError) as e:
            print(f'{e}', file=sys.stderr)
            status = 1
    return status


if __name__ == '__main__':
    sys.exit(main())
