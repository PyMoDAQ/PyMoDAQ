import json

from pymodaq.utils.plugin_testing import compliance_report as cr

STUB_OK = 'from pymodaq.utils.plugin_testing import PluginPackageChecks'
CALLER = f'uses: {cr.TEMPLATE}/.github/workflows/%s@5.3.x'


def make_request(files: dict, owner: str = 'PyMoDAQ', pulls: list = None):
    tree = [{'path': p} for p in files]

    def request(url, raw=False):
        if url.endswith('/pulls?state=open&per_page=100'):
            return pulls or []
        if '/git/trees/' in url:
            return {'tree': tree}
        if url.startswith(cr.API + '/repos/'):
            return {'default_branch': 'main', 'owner': {'login': owner}}
        return files[url.split('/main/', 1)[1]]
    return request


COMPLIANT = {
    'AGENTS.md': '', 'CLAUDE.md': '',
    'tests/test_plugin_package_structure.py': STUB_OK,
    '.github/workflows/tests.yml': CALLER % 'reusable-tests.yml',
    '.github/workflows/compatibility.yml': CALLER % 'reusable-compatibility.yml',
    '.github/workflows/python-publish.yml': CALLER % 'reusable-publish.yml',
    'pyproject.toml': 'dependencies = [\n "pymodaq>=5.3.2",\n]',
}


def test_parse_floor():
    assert cr.parse_floor('"pymodaq>=5.3.2",') == (5, 3, 2)
    assert cr.parse_floor("'pymodaq >= 4.4'") == (4, 4, 0)
    assert cr.parse_floor('"pymodaq_gui>=5.3.0"') is None


def test_full_name_of():
    assert cr.full_name_of('basler') == 'PyMoDAQ/pymodaq_plugins_basler'
    assert cr.full_name_of('pymodaq_plugins_asi') == 'PyMoDAQ/pymodaq_plugins_asi'
    assert cr.full_name_of('someone/pymodaq_plugins_x') == 'someone/pymodaq_plugins_x'


def test_compliant_repository(monkeypatch):
    monkeypatch.setattr(cr, 'request', make_request(COMPLIANT))
    monkeypatch.setattr(cr, 'fetch', lambda full_name, branch, path: COMPLIANT[path])
    result = cr.check('PyMoDAQ/pymodaq_plugins_good')
    assert result['compliant'], result


def test_old_repository_and_outside_host(monkeypatch):
    old = {'tests/test_plugin_package_structure.py': 'import pymodaq_utils', '.github/workflows/Test.yml': '',
           'pyproject.toml': '"pymodaq>=4.4.7"'}
    monkeypatch.setattr(cr, 'request', make_request(old, owner='someone', pulls=[
        {'number': 3, 'title': 'Use the plugin acceptance checks', 'head': {'ref': 'x'}},
        {'number': 4, 'title': 'Follow the plugin template: shared workflows', 'head': {'ref': 'y'}},
        {'number': 5, 'title': 'Unrelated', 'head': {'ref': 'feature/plugin_acceptance_tests'}},
        {'number': 6, 'title': 'Unrelated', 'head': {'ref': 'z'}}]))
    monkeypatch.setattr(cr, 'fetch', lambda full_name, branch, path: old.get(path, ''))
    result = cr.check('someone/pymodaq_plugins_old', {'pymodaq_plugins_old': ('1.0.0', 'someone/pymodaq_plugins_old')})
    assert result['host'].startswith('OUTSIDE someone')
    assert result['agents'].startswith('MISSING')
    assert result['tests'].startswith('OLD')
    assert 'legacy Test.yml' in result['workflows'] and 'no tests.yml' in result['workflows']
    assert result['floor'] == 'OLD pymodaq>=4.4.7'
    assert result['pr'] == '#3 #4 #5'
    assert not result['compliant']


def test_render_counts_compliant_rows():
    rows = [{'repo': 'a', 'compliant': True}, {'repo': 'b', 'compliant': False}]
    assert render_last(rows) == '1/2 repositories follow the template'
    assert json.loads(json.dumps(rows)) == rows


def render_last(rows):
    return cr.render(rows).splitlines()[-1]
