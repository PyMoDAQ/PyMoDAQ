"""Operating systems and processor architectures supported by an instrument plugin.

A plugin that only works on some systems (a Windows driver, a Raspberry Pi board...) declares it in the class of its
instrument plugin::

    class DAQ_Move_Xxxx(DAQ_Move_base):
        supported_platforms = ('win32',)                   # values of sys.platform: 'win32', 'linux', 'darwin'
        supported_architectures = ('aarch64', 'armv7l')    # optional, values of platform.machine()

``None`` (the default of the base classes) means all of them. PyMoDAQ then refuses to initialize the plugin on another
system, with a message, and ``check_plugin`` reads the declaration to check (and update with ``--fix-classifiers``)
the ``Operating System`` classifiers of the ``pyproject.toml``.

.. versionadded:: 5.3.5
"""
from __future__ import annotations

import ast
import platform
import re
import sys
from pathlib import Path
from typing import Iterable, Optional

#: values of ``sys.platform`` and the matching name and PyPI classifier
PLATFORMS = {
    'win32': ('Windows', 'Operating System :: Microsoft :: Windows'),
    'linux': ('Linux', 'Operating System :: POSIX :: Linux'),
    'darwin': ('macOS', 'Operating System :: MacOS'),
}
OS_INDEPENDENT = 'Operating System :: OS Independent'

#: values of ``platform.machine()`` (compared without case), with their aliases
ARCHITECTURES = {
    'x86_64': ('x86_64', 'amd64'),
    'i686': ('i686', 'i386', 'x86'),
    'aarch64': ('aarch64', 'arm64'),
    'armv7l': ('armv7l', 'armv8l'),
    'armv6l': ('armv6l',),
}
_ARCH_ALIASES = {alias: name for name, aliases in ARCHITECTURES.items() for alias in aliases}

PLUGIN_CLASS_RE = re.compile(r'^DAQ_(Move|[0-2N]DViewer)_\w+$')
_OS_CLASSIFIER_RE = re.compile(r'^(?P<indent>\s*)(?P<quote>["\'])Operating System ::.*$')


def _as_tuple(value) -> Optional[tuple]:
    if value is None:
        return None
    return (value,) if isinstance(value, str) else tuple(value)


def normalize_architecture(machine: str) -> str:
    """Canonical name of an architecture (``arm64`` -> ``aarch64``...), the lowercased input if unknown"""
    return _ARCH_ALIASES.get(machine.lower(), machine.lower())


def describe(platforms: Optional[Iterable[str]] = None, architectures: Optional[Iterable[str]] = None) -> str:
    """Text for the user, for instance ``Linux (aarch64, armv7l)``; empty if there is no restriction"""
    platforms, architectures = _as_tuple(platforms), _as_tuple(architectures)
    text = ' or '.join(PLATFORMS.get(p, (p,))[0] for p in platforms) if platforms else ''
    if architectures:
        arch = ', '.join(architectures)
        text = f'{text} ({arch})' if text else f'the architectures {arch}'
    return text


def unsupported_reason(platforms: Optional[Iterable[str]] = None, architectures: Optional[Iterable[str]] = None,
                       system: Optional[str] = None, machine: Optional[str] = None) -> str:
    """Why a plugin cannot run on this computer, or an empty string if it can

    Parameters
    ----------
    platforms: iterable of str or None
        values of ``sys.platform`` the plugin works on (``None``: all). A prefix is enough: ``linux`` matches
        ``linux2``
    architectures: iterable of str or None
        values of ``platform.machine()`` the plugin works on (``None``: all)
    system, machine: str
        replace ``sys.platform`` and ``platform.machine()``, for tests
    """
    platforms, architectures = _as_tuple(platforms), _as_tuple(architectures)
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    ok_system = not platforms or any(system.startswith(p) for p in platforms)
    ok_machine = not architectures or normalize_architecture(machine) in {normalize_architecture(a)
                                                                         for a in architectures}
    if ok_system and ok_machine:
        return ''
    return f'This plugin only works on {describe(platforms, architectures)} (this computer: {system}, {machine})'


def classifiers_for(platforms: Optional[Iterable[str]] = None) -> list[str]:
    """The ``Operating System`` classifiers of a plugin working on these systems (``None``: OS independent)"""
    platforms = _as_tuple(platforms)
    if not platforms:
        return [OS_INDEPENDENT]
    return [PLATFORMS[p][1] for p in PLATFORMS if p in platforms]


def invalid_values(platforms: Optional[Iterable[str]], architectures: Optional[Iterable[str]]) -> list[str]:
    """Problems of a declaration: unknown system or architecture names, empty lists"""
    problems = []
    platforms, architectures = _as_tuple(platforms), _as_tuple(architectures)
    if platforms is not None:
        if not platforms:
            problems.append('supported_platforms is empty, use None for all the systems')
        problems.extend(f"unknown system '{p}' in supported_platforms, use {list(PLATFORMS)}"
                        for p in platforms if p not in PLATFORMS)
    if architectures is not None:
        if not architectures:
            problems.append('supported_architectures is empty, use None for all the architectures')
        problems.extend(f"unknown architecture '{a}' in supported_architectures, use values of platform.machine() "
                        f"like {list(ARCHITECTURES)}" for a in architectures if normalize_architecture(a) not in
                        ARCHITECTURES)
    return problems


def declared_in_class(cls: ast.ClassDef) -> tuple[Optional[tuple], Optional[tuple]]:
    """``(supported_platforms, supported_architectures)`` written in the body of a plugin class (None if absent or
    not a literal)"""
    found = {}
    for node in cls.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets, value = [t for t in node.targets if isinstance(t, ast.Name)], node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            targets, value = [node.target], node.value
        for target in targets:
            if target.id in ('supported_platforms', 'supported_architectures'):
                try:
                    found[target.id] = _as_tuple(ast.literal_eval(value))
                except (ValueError, SyntaxError):
                    pass
    return found.get('supported_platforms'), found.get('supported_architectures')


def package_platforms(root: Path) -> Optional[set]:
    """Systems on which the instruments of a plugin package work (union over the instrument modules), read from the
    sources. ``None`` if at least one instrument works on all of them"""
    systems: set = set()
    files = sorted(set(root.rglob('daq_move_*.py')) | set(root.rglob('daq_*viewer_*.py')))
    for file in files:
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and PLUGIN_CLASS_RE.match(n.name)):
            declared, _ = declared_in_class(cls)
            if not declared:
                return None
            systems.update(declared)
    return systems or None


def pyproject_os_classifiers(classifiers: Iterable[str]) -> list[str]:
    return [c for c in classifiers if c.startswith('Operating System ::')]


def update_pyproject_classifiers(pyproject: Path, platforms: Optional[Iterable[str]]) -> bool:
    """Replace the ``Operating System`` classifiers in the ``classifiers`` list of a ``pyproject.toml`` (a text edit,
    the rest of the file is kept). Returns True if the file changed"""
    wanted = classifiers_for(platforms)
    lines = pyproject.read_text(encoding='utf-8').splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if re.match(r'^\s*classifiers\s*=\s*\[', line)), None)
    if start is None:
        raise ValueError('no classifiers = [...] list in the pyproject.toml (dynamic classifiers?)')
    end = next((i for i in range(start, len(lines)) if lines[i].strip().startswith(']') or
                (i == start and lines[i].rstrip().endswith(']'))), None)
    if end is None or end == start:
        raise ValueError('the classifiers list must be written on several lines')
    indexes = [i for i in range(start + 1, end) if _OS_CLASSIFIER_RE.match(lines[i])]
    sample = lines[indexes[0]] if indexes else lines[end - 1]
    indent = re.match(r'\s*', sample).group(0) or '    '
    quote = '"'
    new = [f'{indent}{quote}{c}{quote},\n' for c in wanted]
    if indexes:
        first = indexes[0]
        rebuilt = [line for i, line in enumerate(lines) if i not in indexes]
        rebuilt[first:first] = new
    else:
        rebuilt = lines[:end] + new + lines[end:]
        if lines[end - 1].rstrip().endswith('"') or lines[end - 1].rstrip().endswith("'"):
            rebuilt[end - 1] = lines[end - 1].rstrip() + ',\n'
    changed = rebuilt != lines
    if changed:
        pyproject.write_text(''.join(rebuilt), encoding='utf-8')
    return changed


#: Python versions PyMoDAQ is developed for, they give the ``Programming Language :: Python`` classifiers
PYTHON_VERSIONS = ('3.10', '3.11', '3.12', '3.13')


def python_classifiers(requires_python: str = '') -> list[str]:
    """``Programming Language :: Python :: 3.x`` for each of :data:`PYTHON_VERSIONS` accepted by ``requires-python``
    (all of them if empty or invalid)"""
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    try:
        spec = SpecifierSet(requires_python or '')
    except InvalidSpecifier:
        spec = SpecifierSet('')
    return [f'Programming Language :: Python :: {v}' for v in PYTHON_VERSIONS if spec.contains(f'{v}.0')]


def dynamic_classifiers(pyproject: dict, package_folder: Path) -> list[str]:
    """The classifiers of a plugin whose ``classifiers`` field is *dynamic* in the ``pyproject.toml``: those listed in
    ``[tool.pymodaq] classifiers`` (the ``Operating System`` and ``Programming Language :: Python :: 3.x`` ones are
    ignored) followed by the Python versions accepted by ``requires-python`` and the systems computed from the
    ``supported_platforms`` of its instrument plugins. Used by the hatch metadata hook at build time"""
    listed = pyproject.get('tool', {}).get('pymodaq', {}).get('classifiers', [])
    kept = [c for c in listed if not c.startswith(('Operating System ::', 'Programming Language :: Python :: 3.'))]
    return (kept + python_classifiers(pyproject.get('project', {}).get('requires-python', '')) +
            classifiers_for(package_platforms(package_folder)))


def _imported_files(path: Path, root: Path) -> set:
    """Python files of the package imported by a module (absolute ``pymodaq_plugins_x.hardware.y`` or relative)"""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()
    found = set()

    def add(parts: list):
        target = root.joinpath(*parts)
        for candidate in (target.with_suffix('.py'), target / '__init__.py'):
            if candidate.is_file():
                found.add(candidate)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split('.')
                if parts[0] == root.name:
                    add(parts[1:])
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or '').split('.') if node.module else []
            if node.level:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                try:
                    parts = list(base.relative_to(root).parts) + module
                except ValueError:
                    continue
            elif module[0] == root.name:
                parts = module[1:]
            else:
                continue
            add(parts)
            for alias in node.names:
                add(parts + [alias.name])
    return found


def windows_only_files(root: Path) -> set:
    """Python files of a plugin package that only the Windows-only instruments use (directly or through the other
    modules): code that only works on Windows is expected there. All of them if every instrument declares
    ``supported_platforms = ('win32',)``. Files used by an instrument working elsewhere are never in it"""
    files = [f for f in sorted(root.rglob('*.py')) if '__pycache__' not in f.parts]
    if package_platforms(root) == {'win32'}:
        return set(files)
    graph = {f: _imported_files(f, root) for f in files}

    def reachable(start: Path) -> set:
        seen, todo = {start}, [start]
        while todo:
            for other in graph.get(todo.pop(), ()):
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        return seen

    windows, others = set(), set()
    for f in files:
        if not (f.name.startswith('daq_move_') or re.match(r'daq_\w*viewer_', f.name)):
            continue
        try:
            tree = ast.parse(f.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        declared = [declared_in_class(c)[0] for c in tree.body
                    if isinstance(c, ast.ClassDef) and PLUGIN_CLASS_RE.match(c.name)]
        (windows if declared and all(d and set(d) == {'win32'} for d in declared) else others).update(reachable(f))
    return windows - others


def platforms_as_rst() -> str:
    """The accepted values as two reStructuredText tables, to be included in the documentation"""
    out = ['.. list-table::', '   :header-rows: 1', '   :widths: 20 20 60', '',
           '   * - ``supported_platforms``', '     - System', '     - Classifier']
    for key, (label, classifier) in PLATFORMS.items():
        out += [f'   * - ``{key}``', f'     - {label}', f'     - ``{classifier}``']
    out += ['', '.. list-table::', '   :header-rows: 1', '   :widths: 30 70', '',
            '   * - ``supported_architectures``', '     - Also accepted (same architecture)']
    for key, aliases in ARCHITECTURES.items():
        other = ', '.join(f'``{a}``' for a in aliases if a != key)
        out += [f'   * - ``{key}``', f'     - {other}']
    out.append('')
    return '\n'.join(out)
