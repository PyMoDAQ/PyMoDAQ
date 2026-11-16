"""The code of the tutorial 'Your first plugin in 10 minutes' is written to a package, checked and run."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from pymodaq_utils.plugin_tools.rules import check_plugin_source

PAGE = Path(__file__).parents[4] / 'docs' / 'src' / 'tutorials' / 'first_plugin.rst'
BLOCK_RE = re.compile(r'\.\. code-block:: python\n   :caption: (?P<path>\S+)\n\n(?P<code>(?:   .*\n|\n)+)')


@pytest.fixture
def written_package(tmp_path):
    if not PAGE.is_file():
        pytest.skip('docs not available (installed package)')
    blocks = {m['path']: re.sub(r'^   ', '', m['code'], flags=re.M).rstrip() + '\n'
              for m in BLOCK_RE.finditer(PAGE.read_text())}
    assert len(blocks) == 4, sorted(blocks)
    for path, code in blocks.items():
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(code)
    for folder in (tmp_path / 'pymodaq_plugins_acme').rglob('*'):
        if folder.is_dir():
            (folder / '__init__.py').touch()
    (tmp_path / 'pymodaq_plugins_acme' / '__init__.py').touch()
    return tmp_path


def test_plugins_are_short_and_pass_the_static_rules(written_package):
    package = written_package / 'pymodaq_plugins_acme'
    for path, kind, name in ((package / 'daq_move_plugins' / 'daq_move_Acme.py', 'move', 'DAQ_Move_Acme'),
                             (package / 'daq_viewer_plugins' / 'plugins_1D' / 'daq_1Dviewer_Acme.py', 'viewer',
                              'DAQ_1DViewer_Acme')):
        assert len(path.read_text().splitlines()) <= 80, path.name
        assert check_plugin_source(path, kind, name, static_fallback=True) == []


def test_the_test_of_the_page_passes(written_package):
    env = {**os.environ, 'PYTHONPATH': str(written_package), 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                             str(written_package / 'tests' / 'test_acme.py')],
                            cwd=written_package, env=env, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
