"""The pymodaq_migrate command migrates the files written by older versions without touching the originals."""
import pickle

from pymodaq.utils.migrate import main


def test_a_layout_file_is_migrated(tmp_path, capsys):
    source = tmp_path / 'legacy.dock'
    source.write_bytes(pickle.dumps({'main': ('vertical', [], {}), 'float': []}))

    assert main([str(source)]) == 0

    assert (tmp_path / 'legacy_migrated.dock').is_file()
    assert 'legacy_migrated.dock' in capsys.readouterr().out


def test_the_destination_can_be_chosen(tmp_path):
    source = tmp_path / 'legacy.dock'
    source.write_bytes(pickle.dumps({'main': ('vertical', [], {}), 'float': []}))

    assert main([str(source), '--output', str(tmp_path / 'chosen.dock')]) == 0

    assert (tmp_path / 'chosen.dock').is_file()


def test_unknown_file_types_are_refused(tmp_path, capsys):
    source = tmp_path / 'something.txt'
    source.write_text('text')

    assert main([str(source)]) != 0
    assert 'something.txt' in capsys.readouterr().err


def test_a_missing_file_is_reported(tmp_path, capsys):
    assert main([str(tmp_path / 'missing.dock')]) != 0
    assert 'missing.dock' in capsys.readouterr().err


def test_a_doubtful_file_is_refused(tmp_path, capsys):
    source = tmp_path / 'doubtful.dock'
    source.write_bytes(pickle.dumps(print))  # a reference to a function, not plain data

    assert main([str(source)]) != 0
    assert not (tmp_path / 'doubtful_migrated.dock').exists()
    assert 'refused' in capsys.readouterr().err.lower()
