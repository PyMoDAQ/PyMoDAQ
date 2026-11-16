"""The extensions of PyMoDAQ follow the rules that check_plugin applies to the extensions of the plugins"""
from pathlib import Path

import pymodaq.extensions
from pymodaq_utils.plugin_tools.rules import check_extension_source

FOLDER = Path(pymodaq.extensions.__file__).parent


def test_core_extensions_follow_the_rules():
    # the core extensions are registered in pymodaq.extensions, they don't define EXTENSION_NAME and CLASS_NAME
    # (PMQ330) but when they do, these must be right
    findings = [f for path in sorted(FOLDER.rglob('*.py')) if '__pycache__' not in path.parts
                for f in check_extension_source(path) if f.code != 'PMQ330']
    assert findings == [], '\n'.join(str(f) for f in findings)
