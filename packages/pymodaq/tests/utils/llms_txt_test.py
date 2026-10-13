"""The curated llms.txt of the documentation only points to pages that exist"""
import re
from pathlib import Path

import pytest

DOCS = Path(__file__).parents[4] / 'docs' / 'src'
LLMS = DOCS / '_extra' / 'llms.txt'
BASE = 'https://pymodaq.cnrs.fr/en/stable/'

pytestmark = pytest.mark.skipif(not LLMS.is_file(), reason='docs not available (installed package)')


def test_llms_txt_has_the_expected_structure():
    lines = LLMS.read_text().splitlines()
    assert lines[0] == '# PyMoDAQ'
    assert lines[2].startswith('> ')
    assert [line for line in lines if line.startswith('## ')][0] == '## Write an instrument plugin'


def test_pages_of_llms_txt_exist():
    pages = re.findall(r'\]\(' + re.escape(BASE) + r'([^)#]+)\.html\)', LLMS.read_text())
    assert pages
    missing = [page for page in pages if not (DOCS / f'{page}.rst').is_file()]
    assert not missing, f'pages of llms.txt that do not exist: {missing}'


def test_first_plugin_page_comes_first():
    first = re.search(r'\]\((https://[^)]+)\)', LLMS.read_text()).group(1)
    assert first == BASE + 'tutorials/first_plugin.html'
