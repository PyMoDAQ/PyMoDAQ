"""Guard of the layering of the packages of the monorepo: a package never imports the ones above it

The order is the one of ``install-packages.py``. The few upward imports that remain are listed below, with the reason
why they are accepted. Any other one fails this test; so does an entry that is not needed anymore.
"""
import ast
from pathlib import Path

import pytest

PACKAGES_DIR = Path(__file__).parents[2]
ORDER = ['pymodaq_utils', 'pymodaq_data', 'pymodaq_gui', 'pymodaq_scripting', 'pymodaq']
RANK = {name: rank for rank, name in enumerate(ORDER)}

TYPING = 'only imported for type checking (under TYPE_CHECKING)'
LAZY = 'imported when called, only if the package above is installed'

# (file relative to packages/<package>/src, imported module) -> why it is accepted
ALLOWED = {
    ('pymodaq_utils/config.py', 'pymodaq_gui.parameter'): TYPING,
    ('pymodaq_utils/config.py', 'pymodaq_gui.utils.widgets.tree_toml'): LAZY + ' (config editor)',
    ('pymodaq_utils/config.py', 'pymodaq_gui.parameter.ioxml'): LAZY + ' (config editor)',
    ('pymodaq_utils/plugin_testing.py', 'pymodaq.utils.plugin_testing'): LAZY + ' (moved there, kept for old imports)',
    ('pymodaq_utils/plugin_tools/checks.py', 'pymodaq.control_modules.move_utility_classes'):
        LAZY + ' (checks of the plugins need their base classes)',
    ('pymodaq_utils/plugin_tools/checks.py', 'pymodaq.control_modules.viewer_utility_classes'):
        LAZY + ' (checks of the plugins need their base classes)',
    ('pymodaq_utils/plugin_tools/rules.py', 'pymodaq_data'): LAZY + ' (rules about data)',
    ('pymodaq_utils/serialize/serializer_legacy.py', 'pymodaq_data.data'): TYPING,
    ('pymodaq_gui/utils/app_worker.py', 'pymodaq.utils.managers.modules'): TYPING,
    # DataActuator is a DataWithAxes flavour declared in pymodaq because it is specific to the move plugins
    ('pymodaq_scripting/devices.py', 'pymodaq.utils.data'): TYPING,
    ('pymodaq_scripting/utils.py', 'pymodaq.utils.data'): TYPING,
}


def upward_imports(package: str) -> set[tuple[str, str]]:
    src = PACKAGES_DIR / package / 'src'
    found = set()
    for path in sorted(src.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or '']
            else:
                continue
            for name in names:
                if RANK.get(name.split('.')[0], -1) > RANK[package]:
                    found.add((path.relative_to(src).as_posix(), name))
    return found


@pytest.fixture(scope='module')
def found() -> set[tuple[str, str]]:
    if not all((PACKAGES_DIR / package / 'src').is_dir() for package in ORDER):
        pytest.skip('needs the sources of the five packages of the monorepo')
    return {item for package in ORDER[:-1] for item in upward_imports(package)}


def test_no_unlisted_import_of_a_package_above(found):
    unlisted = sorted(found - set(ALLOWED))
    assert not unlisted, (f'Packages must not import the ones above them ({" < ".join(ORDER)}), '
                          f'rework or, if unavoidable, list them in ALLOWED with the reason: {unlisted}')


def test_no_obsolete_entry_in_the_allowed_imports(found):
    obsolete = sorted(set(ALLOWED) - found)
    assert not obsolete, f'These imports are gone, remove them from ALLOWED: {obsolete}'


def test_install_order_is_the_layering_order():
    install = (PACKAGES_DIR.parent / 'install-packages.py')
    if not install.is_file():
        pytest.skip('install-packages.py not available')
    tree = ast.parse(install.read_text(encoding='utf-8'))
    order = [ast.literal_eval(node.value) for node in ast.walk(tree)
             if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'PYMODAQ_PACKAGES'][0]
    assert order == ORDER
