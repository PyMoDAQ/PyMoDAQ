import textwrap

import pytest

from pymodaq_utils.plugin_tools import rules as pr
from pymodaq_utils.plugin_tools.rules import Severity

GOOD = '''
from qtpy import QtWidgets
from pymodaq.utils.custom_ext import CustomExt

EXTENSION_NAME = 'My extension'
CLASS_NAME = 'MyExtension'


class MyExtension(CustomExt):
    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.setup_ui()

    def setup_docks_and_widgets(self):
        pass

    def setup_menus_and_toolbars(self, menubar=None):
        pass


def main():
    from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
    ExperimentManager()
'''


@pytest.fixture
def check(tmp_path):
    def run(code, name='my_ext.py'):
        path = tmp_path / 'extensions' / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(textwrap.dedent(code))
        return pr.check_extension_source(path)
    return run


def codes(findings):
    return {f.code for f in findings}


def test_a_correct_extension_has_no_finding(check):
    assert check(GOOD) == []


def test_helper_module_is_not_an_extension(check):
    assert check('def helper():\n    return 1\n', 'helper.py') == []


@pytest.mark.parametrize('missing', ['EXTENSION_NAME', 'CLASS_NAME'])
def test_missing_names(check, missing):
    code = '\n'.join(line for line in GOOD.splitlines() if not line.startswith(missing))
    findings = check(code)
    assert 'PMQ330' in codes(findings)
    assert next(f for f in findings if f.code == 'PMQ330').severity == Severity.ERROR
    assert missing in next(f for f in findings if f.code == 'PMQ330').message


def test_class_name_does_not_match(check):
    findings = check(GOOD.replace("CLASS_NAME = 'MyExtension'", "CLASS_NAME = 'Other'"))
    assert codes(findings) == {'PMQ331'}


def test_class_name_may_be_imported(check):
    code = GOOD.replace("CLASS_NAME = 'MyExtension'", "CLASS_NAME = 'Other'") + '\nfrom somewhere import Other\n'
    assert check(code) == []


def test_custom_app_is_not_an_extension(check):
    findings = check(GOOD.replace('(CustomExt)', '(CustomApp)').replace('CustomExt', 'CustomApp'))
    assert 'PMQ332' in codes(findings)


def test_derivation_is_followed_in_the_module(check):
    code = GOOD + '\n\nclass Base(CustomExt):\n    pass\n'
    code = code.replace('class MyExtension(CustomExt)', 'class MyExtension(Base)')
    assert 'PMQ332' not in codes(check(code))


def test_deprecated_imports(check):
    findings = check('from pymodaq.utils.parameter import utils\nimport pymodaq.utils.messenger\n' + GOOD)
    assert [f.code for f in findings if f.code == 'PMQ333'] == ['PMQ333', 'PMQ333']
    assert 'pymodaq_gui.parameter' in findings[0].hint


def test_deprecated_hooks(check):
    code = GOOD.replace('setup_docks_and_widgets', 'setup_docks').replace('setup_menus_and_toolbars', 'setup_menu')
    findings = check(code)
    assert [f.code for f in findings] == ['PMQ334', 'PMQ334']


def test_own_managers(check):
    code = GOOD.replace('        self.setup_ui()', '        self.em = ExperimentManager()\n        self.setup_ui()')
    assert codes(check(code)) == {'PMQ335'}


def test_own_modules_manager_is_fine(check):
    code = GOOD.replace('        self.setup_ui()', '        self.mm = ModulesManager([], [])\n        self.setup_ui()')
    assert codes(check(code)) == set()


def test_init_signature_and_setup_ui(check):
    assert codes(check(GOOD.replace('(self, parent, dashboard)', '(self, parent)'))) == {'PMQ336'}
    findings = check(GOOD.replace('        self.setup_ui()\n', ''))
    assert codes(findings) == {'PMQ337'}


def test_noqa(check):
    code = GOOD.replace('def setup_docks_and_widgets(self):', 'def setup_docks(self):  # noqa: PMQ334')
    assert check(code) == []


def test_check_extensions_looks_at_the_extensions_folder(tmp_path):
    folder = tmp_path / 'extensions'
    folder.mkdir()
    (folder / '__init__.py').write_text('')
    (folder / '_private.py').write_text('EXTENSION_NAME = "x"')
    (folder / 'good.py').write_text(GOOD)
    (folder / 'bad.py').write_text(GOOD.replace('CLASS_NAME', 'CLASSNAME'))
    findings = pr.check_extensions(tmp_path)
    assert {(f.path.name, f.code) for f in findings} == {('bad.py', 'PMQ330')}
    assert pr.check_extensions(tmp_path / 'nothing') == []


def test_the_template_extension_is_clean():
    import importlib.util
    spec = importlib.util.find_spec('pymodaq_plugins_template')
    if spec is None or not spec.submodule_search_locations:
        pytest.skip('pymodaq_plugins_template not installed')
    from pathlib import Path
    assert pr.check_extensions(Path(list(spec.submodule_search_locations)[0])) == []
