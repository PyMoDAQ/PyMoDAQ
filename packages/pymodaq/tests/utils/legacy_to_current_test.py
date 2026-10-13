"""The "legacy to current" page of the documentation is generated from the deprecation warnings of the code"""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[4] / 'docs' / 'legacy_to_current.py'

pytestmark = pytest.mark.skipif(not SCRIPT.is_file(), reason='docs not available (installed package)')


@pytest.fixture(scope='module')
def legacy():
    spec = importlib.util.spec_from_file_location('legacy_to_current', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_known_deprecations_are_listed(legacy):
    entries = legacy.collect()
    assert any(module == 'pymodaq.control_modules.daq_move' and 'ini_stage is deprecated, use ini_hardware' in message
               for module, _, message in entries)
    assert any(module == 'pymodaq.utils.math_utils' and not scope for module, scope, _ in entries)


def test_page_is_up_to_date(legacy):
    assert legacy.PAGE.read_text(encoding='utf-8') == legacy.page(), \
        'regenerate the page with: python docs/legacy_to_current.py'
