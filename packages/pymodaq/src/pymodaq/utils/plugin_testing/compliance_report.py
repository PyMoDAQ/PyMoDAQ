"""Report which plugin repositories still do not follow the plugin template.

Maintainer tool, run by hand (it only reads GitHub and PyPI, never writes)::

    python -m pymodaq.utils.plugin_testing.compliance_report                   # every pymodaq_plugins_* repo of the org
    python -m pymodaq.utils.plugin_testing.compliance_report basler thorlabs   # these ones of the PyMoDAQ organization
    python -m pymodaq.utils.plugin_testing.compliance_report someone/pymodaq_plugins_x   # any repository
    python -m pymodaq.utils.plugin_testing.compliance_report --pypi            # + every plugin published on PyPI
    python -m pymodaq.utils.plugin_testing.compliance_report --markdown        # paste in an issue or a message

Archived repositories and forks of the organization are skipped. Set ``GH_TOKEN`` (or have the ``gh`` command logged
in) to raise the GitHub rate limit; public repositories do not need more.

Columns (each ``ok`` or what is wrong):

* ``host``: where the repository lives. A plugin published on PyPI should live in the PyMoDAQ organization (its
  author stays the maintainer); anything else is shown as ``OUTSIDE owner``. ``-`` when the PyPI link and GitHub agree.
* ``agents``: ``AGENTS.md`` and ``CLAUDE.md`` at the root.
* ``tests``: ``tests/test_plugin_package_structure.py`` imports :mod:`pymodaq.utils.plugin_testing` (PyMoDAQ >= 5.3.2).
* ``workflows``: ``tests.yml``, ``compatibility.yml`` and ``python-publish.yml`` call the reusable workflows of
  ``pymodaq_plugins_template`` and no legacy ``Test.yml``, ``Testbase.yml`` or ``updater.yml`` is left.
* ``floor``: the ``pymodaq>=X`` dependency of ``pyproject.toml`` is at least the one of the template.
* ``pr``: open pull request(s) about the plugin acceptance checks, to update instead of duplicating.

.. versionadded:: 5.3.3
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

ORG = 'PyMoDAQ'
TEMPLATE = f'{ORG}/pymodaq_plugins_template'
CALLERS = {'tests.yml': 'reusable-tests.yml', 'compatibility.yml': 'reusable-compatibility.yml',
           'python-publish.yml': 'reusable-publish.yml'}
LEGACY = ('Test.yml', 'Testbase.yml', 'updater.yml')
FLOOR = (5, 3, 2)
API = 'https://api.github.com'
COLUMNS = ['repo', 'host', 'agents', 'tests', 'workflows', 'floor', 'pr']


def _urlopen(url: str, use_token: bool) -> str:
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'plugins-compliance-report'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if use_token and token:
        headers['Authorization'] = f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read().decode()


def request(url: str, raw: bool = False):
    """GET an url; GitHub API urls go through the ``gh`` command when it is available (credentials, rate limit)"""
    if url.startswith(API) and shutil.which('gh'):
        done = subprocess.run(['gh', 'api', url[len(API):]], capture_output=True, text=True)
        if done.returncode == 0:
            return json.loads(done.stdout)
    # an invalid token is refused (a raw file even answers 404) while public data needs none: try both ways
    last_error = None
    for use_token in ((True, False) if url.startswith(API) else (False, True)):
        try:
            body = _urlopen(url, use_token)
            return body if raw else json.loads(body)
        except urllib.error.HTTPError as error:
            last_error = error
    raise last_error


def fetch(full_name: str, branch: str, path: str) -> str:
    try:
        return request(f'https://raw.githubusercontent.com/{full_name}/{branch}/{path}', raw=True)
    except urllib.error.HTTPError:
        return ''


def parse_floor(pyproject: str) -> Optional[Tuple[int, ...]]:
    match = re.search(r'["\']pymodaq\s*>=\s*(\d+)\.(\d+)(?:\.(\d+))?', pyproject)
    return tuple(int(g or 0) for g in match.groups()) if match else None


def org_repos() -> List[str]:
    """Names of the not archived, not forked ``pymodaq_plugins_*`` repositories of the organization"""
    repos, page = [], 1
    while True:
        batch = request(f'{API}/orgs/{ORG}/repos?per_page=100&type=public&page={page}')
        if not batch:
            break
        repos += batch
        page += 1
    return sorted(f"{ORG}/{r['name']}" for r in repos
                  if r['name'].startswith('pymodaq_plugins_') and not r['archived'] and not r['fork']
                  and r['full_name'] != TEMPLATE)


def pypi_plugins() -> dict:
    """``{normalized pypi name: (version, github owner/repo or None)}`` of the plugins published on PyPI"""
    with urllib.request.urlopen(urllib.request.Request(
            'https://pypi.org/simple/', headers={'Accept': 'application/vnd.pypi.simple.v1+json'}), timeout=120) as r:
        index = json.load(r)
    plugins = {}
    for project in index['projects']:
        name = project['name'].lower().replace('-', '_')
        if not name.startswith('pymodaq_plugins_') or name == 'pymodaq_plugins_template':
            continue
        with urllib.request.urlopen(f"https://pypi.org/pypi/{project['name']}/json", timeout=30) as r:
            info = json.load(r)['info']
        urls = ' '.join([info.get('home_page') or ''] + list((info.get('project_urls') or {}).values()))
        found = re.search(r'github\.com/([^/\s]+)/([^/\s#]+)', urls)
        plugins[name] = (info['version'], f'{found.group(1)}/{found.group(2)}' if found else None)
    return plugins


def check(full_name: str, pypi: Optional[dict] = None) -> dict:
    """Compare one repository with what the template ships today"""
    name = full_name.split('/')[-1]
    info = request(f'{API}/repos/{full_name}')
    branch = info['default_branch']
    tree = {t['path'] for t in request(f'{API}/repos/{full_name}/git/trees/{branch}?recursive=1')['tree']}
    result = {'repo': full_name if not full_name.startswith(ORG + '/') else name, 'branch': branch}

    owner = info['owner']['login']
    published = (pypi or {}).get(name.lower().replace('-', '_'))
    if owner != ORG and published:
        result['host'] = f'OUTSIDE {owner} (on PyPI {published[0]})'
    elif owner != ORG:
        result['host'] = f'outside {owner}, not on PyPI'
    elif published and published[1] and not published[1].lower().startswith(ORG.lower() + '/'):
        result['host'] = f'ok (PyPI links to {published[1].split("/")[0]})'
    else:
        result['host'] = 'ok'

    missing = [f for f in ('AGENTS.md', 'CLAUDE.md') if f not in tree]
    result['agents'] = ('MISSING ' + ', '.join(missing)) if missing else 'ok'

    stub = 'tests/test_plugin_package_structure.py'
    if stub not in tree:
        result['tests'] = 'MISSING'
    else:
        text = fetch(full_name, branch, stub)
        if 'pymodaq.utils.plugin_testing' in text:
            result['tests'] = 'ok'
        elif 'pymodaq_utils.plugin_testing' in text:
            result['tests'] = 'OLD (pymodaq_utils.plugin_testing)'
        else:
            result['tests'] = 'OLD (generic copy of the template tests)'

    problems = []
    for workflow, reusable in CALLERS.items():
        path = f'.github/workflows/{workflow}'
        if path not in tree:
            problems.append(f'no {workflow}')
        elif f'{TEMPLATE}/.github/workflows/{reusable}' not in fetch(full_name, branch, path):
            problems.append(f'{workflow} is not the template caller')
    problems += [f'legacy {f}' for f in LEGACY if f'.github/workflows/{f}' in tree]
    result['workflows'] = '; '.join(problems) or 'ok'

    floor = parse_floor(fetch(full_name, branch, 'pyproject.toml'))
    if floor is None:
        result['floor'] = 'MISSING pymodaq>=X'
    elif floor < FLOOR:
        result['floor'] = 'OLD pymodaq>=' + '.'.join(map(str, floor))
    else:
        result['floor'] = 'ok'

    pulls = request(f'{API}/repos/{full_name}/pulls?state=open&per_page=100')
    mine = [f"#{p['number']}" for p in pulls
            if re.search(r'plugin[ _]acceptance|plugin_testing|follow the plugin template', p['title'] + p['head']['ref'],
                         re.I)]
    result['pr'] = ' '.join(mine) or '-'
    result['compliant'] = (result['host'].startswith('ok') and
                           all(result[k] == 'ok' for k in ('agents', 'tests', 'workflows', 'floor')))
    return result


def render(rows: List[dict], markdown: bool = False) -> str:
    lines = []
    if markdown:
        lines.append('| ' + ' | '.join(COLUMNS) + ' |')
        lines.append('|' + '---|' * len(COLUMNS))
        lines += ['| ' + ' | '.join(str(r.get(c, '')) for c in COLUMNS) + ' |' for r in rows]
    else:
        widths = {c: max(len(c), *(len(str(r.get(c, ''))) for r in rows)) for c in COLUMNS}
        lines.append('  '.join(c.ljust(widths[c]) for c in COLUMNS))
        lines += ['  '.join(str(r.get(c, '')).ljust(widths[c]) for c in COLUMNS) for r in rows]
    counted = [r for r in rows if not r.get('gone')]  # a repository that does not exist cannot follow the template
    done = sum(1 for r in counted if r.get('compliant'))
    lines += ['', f'{done}/{len(counted)} repositories follow the template']
    return '\n'.join(lines)


def full_name_of(arg: str) -> str:
    if '/' in arg:
        return arg
    return f"{ORG}/{arg if arg.startswith('pymodaq_plugins_') else 'pymodaq_plugins_' + arg}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('repos', nargs='*', help='short names of the organization (basler) or owner/repo; '
                                                   'default: all the plugins of the organization')
    parser.add_argument('--pypi', action='store_true',
                        help='also check the repositories linked by the plugins published on PyPI')
    parser.add_argument('--markdown', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    published = pypi_plugins() if args.pypi else {}
    names = [full_name_of(r) for r in args.repos]
    if not args.repos:
        try:
            names = org_repos()
        except urllib.error.HTTPError as error:
            print(f'Cannot list the organization ({error}): give the repositories on the command line',
                  file=sys.stderr)
            return 2
    for _, repo in published.values():  # the template is sometimes the only link an author gave on PyPI
        if repo and repo not in names and repo != TEMPLATE:
            names.append(repo)

    rows = []
    for name in names:
        try:
            rows.append(check(name, published))
        except urllib.error.HTTPError as error:
            gone = error.code == 404  # deleted, renamed or private: the link to it (PyPI, org list) is to be fixed
            rows.append({'repo': name, 'host': 'gone (404)' if gone else f'error {error.code}', 'compliant': False,
                         'gone': gone})
    print(json.dumps(rows, indent=1) if args.json else render(rows, args.markdown))
    return 0 if all(r.get('compliant') for r in rows if not r.get('gone')) else 1


if __name__ == '__main__':
    sys.exit(main())
