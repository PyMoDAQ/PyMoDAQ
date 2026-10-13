"""Check the modules of Dashboard extensions: the ``check_extension`` command.

It applies the rules PMQ330 to PMQ339 (see :func:`pymodaq_utils.plugin_tools.rules.check_extension_source`) to a python
file or to a folder, whether the extension belongs to a plugin package or to PyMoDAQ itself. The sources are read,
nothing is imported. ``check_plugin`` also applies these rules to the ``extensions`` folder of a plugin package.

.. versionadded:: 5.3.7
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

from pymodaq_utils.plugin_tools.checks import FAIL_LEVELS, CheckResult, PluginReport
from pymodaq_utils.plugin_tools.rules import check_extension_source, use_color


def is_core_extension(path: Path) -> bool:
    """Whether a file is in the ``extensions`` of the ``pymodaq`` package: the core extensions are registered in
    ``pymodaq.extensions`` and do not need to define ``EXTENSION_NAME`` and ``CLASS_NAME``"""
    parts = path.resolve().parts
    return any(a == 'pymodaq' and b == 'extensions' for a, b in zip(parts, parts[1:]))


def find_extension_files(target: Path) -> list[Path]:
    """The python files to check: the file itself, or the modules of a folder

    For a folder holding an ``extensions`` folder (the plugin package, or the repository with its ``src`` folder) the
    modules of this folder are taken, otherwise all the modules of the folder and its sub-folders. The ``__init__``
    and the private modules (starting with ``_``) are left out.
    """
    if target.is_file():
        return [target]
    folder = next((c for c in (target / 'extensions', *sorted(target.glob('src/*/extensions')),
                               *sorted(target.glob('pymodaq_plugins_*/extensions'))) if c.is_dir()), target)
    return [p for p in sorted(folder.rglob('*.py'))
            if not p.name.startswith('_') and '__pycache__' not in p.parts]


def check_extension_files(targets: Sequence[str | Path], fail_on: str = 'error',
                          core: Optional[bool] = None) -> PluginReport:
    """Run the extension rules on files or folders and return a report

    Parameters
    ----------
    targets: list of str or Path
        python files of extensions, or folders (see :func:`find_extension_files`)
    fail_on: str
        'error' (default), 'warning' or 'todo', see :data:`pymodaq_utils.plugin_tools.checks.FAIL_LEVELS`
    core: bool
        True for the extensions of PyMoDAQ: PMQ330 (``EXTENSION_NAME`` and ``CLASS_NAME`` missing) is then not
        reported. By default found from the path of each file (``pymodaq/extensions``).
    """
    if fail_on not in FAIL_LEVELS:
        raise ValueError(f'fail_on should be one of {list(FAIL_LEVELS)}')
    results = []
    for target in targets:
        target = Path(target)
        if not target.exists():
            raise FileNotFoundError(target)
        for path in find_extension_files(target):
            is_core = is_core_extension(path) if core is None else core
            findings = [f for f in check_extension_source(path) if not (is_core and f.code == 'PMQ330')]
            try:
                item = path.resolve().relative_to(Path.cwd()).as_posix()
            except ValueError:
                item = str(path)
            results.append(CheckResult(item, findings=findings))
    return PluginReport('extensions', results, fail_on)


def main(argv=None) -> int:
    """Print the report on extension modules: the ``check_extension`` command (or
    ``python -m pymodaq_utils.plugin_tools.extension_checks``)

    Returns 0 if the checks pass, 1 otherwise (so that it can also be used in a script or a CI).
    """
    import argparse
    parser = argparse.ArgumentParser(prog='check_extension',
                                     description='Check the modules of PyMoDAQ Dashboard extensions and print a report')
    parser.add_argument('paths', nargs='+',
                        help='python file of an extension, or folder: the extensions folder of a plugin package or of '
                             'PyMoDAQ, or the plugin repository')
    parser.add_argument('--fail-on', choices=list(FAIL_LEVELS), default='error',
                        help="findings of this level and above give a non zero exit code ('todo': everything)")
    parser.add_argument('--core', action='store_true', default=None,
                        help='the extensions are part of PyMoDAQ: EXTENSION_NAME and CLASS_NAME are not required '
                             '(found from the path by default)')
    parser.add_argument('--color', choices=['auto', 'always', 'never'], default='auto',
                        help='color the report: auto (default) if the output is a terminal and NO_COLOR is not set')
    args = parser.parse_args(argv)
    try:
        report = check_extension_files(args.paths, args.fail_on, args.core)
    except FileNotFoundError as e:
        parser.error(f'{e} does not exist')
    print(report.format(verbose=True, color=use_color(args.color)))
    return 0 if report.ok else 1


if __name__ == '__main__':
    sys.exit(main())
