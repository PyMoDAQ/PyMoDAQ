from pymodaq_utils import help as help_mod
from pymodaq_utils.help import get_help_text


class Dummy:
    pass


def test_no_help_file():
    # no help.md next to pymodaq_utils/tests/help_test.py
    assert get_help_text(Dummy) is None
    assert get_help_text(Dummy()) is None


def test_help_found_for_path_class_and_module(tmp_path):
    (tmp_path / 'help.md').write_text('# Title\n\nSome help é\n', encoding='utf-8')
    assert get_help_text(tmp_path) == '# Title\n\nSome help é\n'
    assert get_help_text(tmp_path / 'module.py') == '# Title\n\nSome help é\n'
    assert get_help_text(str(tmp_path)) == '# Title\n\nSome help é\n'


def test_help_of_a_package_module_without_help():
    assert get_help_text(help_mod) is None
