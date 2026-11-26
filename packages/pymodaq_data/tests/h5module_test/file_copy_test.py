# -*- coding: utf-8 -*-
"""Tests of the automatic copy of the closed files"""
from pathlib import Path
import threading

import pytest

from pymodaq_data.h5modules import file_copy
from pymodaq_data.h5modules.file_copy import FileCopier, CopyError, sha256_of


@pytest.fixture(autouse=True)
def pending_in_tmp(tmp_path, monkeypatch):
    """Keep the list of the copies to retry out of the configuration folder"""
    monkeypatch.setattr(FileCopier, 'pending_file', staticmethod(lambda: tmp_path / 'pending.json'))


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'data' / 'Dataset_20261126' / 'Dataset_20261126_000.h5'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'0123456789' * 1000)
    return path


@pytest.fixture
def copier(tmp_path):
    return FileCopier(enabled=True, destination=tmp_path / 'nas', url_prefix='smb://nas/data/',
                      delay=0.1, source_root=tmp_path / 'data')


class TestCopy:
    def test_copy_is_identical_and_keeps_the_relative_path(self, copier, source, tmp_path):
        result = copier.copy(source)
        expected = tmp_path / 'nas' / 'Dataset_20261126' / 'Dataset_20261126_000.h5'
        assert result.ok
        assert result.destination == expected
        assert expected.read_bytes() == source.read_bytes()
        assert result.sha256 == sha256_of(source)
        assert result.url == 'smb://nas/data/Dataset_20261126/Dataset_20261126_000.h5'
        assert source.exists()

    def test_without_url_prefix_there_is_no_url(self, copier, source):
        copier.configure(url_prefix='')
        assert copier.copy(source).url is None

    def test_file_out_of_the_source_root_keeps_its_folder_and_name(self, copier, tmp_path):
        other = tmp_path / 'elsewhere' / 'run' / 'file.h5'
        other.parent.mkdir(parents=True)
        other.write_bytes(b'abc')
        assert copier.destination_for(other) == tmp_path / 'nas' / 'run' / 'file.h5'

    def test_deepest_source_root_is_used(self, copier, source, tmp_path):
        copier.add_source_root(tmp_path / 'data' / 'Dataset_20261126')
        assert copier.relative_path(source) == Path('Dataset_20261126_000.h5')

    def test_copy_replaces_the_previous_one(self, copier, source):
        first = copier.copy(source)
        source.write_bytes(b'new content')
        second = copier.copy(source)
        assert second.destination.read_bytes() == b'new content'
        assert second.sha256 != first.sha256

    def test_copy_is_not_repeated_when_nothing_changed(self, copier, source, monkeypatch):
        copier.copy(source)
        opened = []
        real_open = open
        monkeypatch.setattr('builtins.open', lambda *a, **k: opened.append(a[0]) or real_open(*a, **k))
        copier.copy(source)
        assert source not in [Path(p) for p in opened]

    def test_source_written_during_the_copy_is_copied_again(self, copier, source, monkeypatch):
        real_sha256 = file_copy.hashlib.sha256
        attempts = []

        def sha256_after_a_write(*args, **kwargs):
            # called at the start of each attempt, once the size and time of the source were read
            attempts.append(1)
            if len(attempts) == 1:
                source.write_bytes(b'written during the copy')
            return real_sha256(*args, **kwargs)

        monkeypatch.setattr(file_copy.hashlib, 'sha256', sha256_after_a_write)
        result = copier.copy(source)
        assert result.destination.read_bytes() == b'written during the copy'
        assert result.sha256 == sha256_of(source)

    def test_gives_up_if_the_source_keeps_changing(self, copier, source, monkeypatch):
        counter = {'n': 0}
        real_stat = Path.stat

        def moving_stat(self, *args, **kwargs):
            st = real_stat(self, *args, **kwargs)
            if self == source:
                counter['n'] += 1
                import os
                return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink, st.st_uid, st.st_gid,
                                       st.st_size + counter['n'], int(st.st_atime), int(st.st_mtime),
                                       int(st.st_ctime), st.st_atime, st.st_mtime, st.st_ctime))
            return st

        monkeypatch.setattr(Path, 'stat', moving_stat)
        with pytest.raises(CopyError):
            copier.copy(source)
        assert not list((copier.destination_for(source).parent).glob('*.part'))


class TestPlanning:
    @staticmethod
    def listen(copier):
        done = threading.Event()
        results = []

        def on_result(result):
            results.append(result)
            done.set()

        copier.add_listener(on_result)
        return done, results

    def test_closed_file_is_copied_after_the_delay(self, copier, source):
        done, results = self.listen(copier)
        copier.on_opened(source)
        copier.on_closed(source)
        assert done.wait(5)
        assert results[0].ok and results[0].destination.exists()

    def test_reopened_file_is_not_copied(self, copier, source):
        copier.configure(delay=0.3)
        done, results = self.listen(copier)
        copier.on_closed(source)
        copier.on_opened(source)
        assert not done.wait(0.8)
        assert results == []
        assert not copier.destination_for(source).exists()

    def test_second_close_postpones_the_copy_and_makes_only_one(self, copier, source):
        copier.configure(delay=0.3)
        done, results = self.listen(copier)
        copier.on_closed(source)
        copier.on_opened(source)
        copier.on_closed(source)
        assert done.wait(5)
        assert done.wait(0.6) and len(results) == 1

    def test_disabled_copier_does_nothing(self, copier, source):
        copier.configure(enabled=False)
        done, results = self.listen(copier)
        copier.on_closed(source)
        assert not done.wait(0.5)

    def test_flush_copies_the_planned_files_now(self, copier, source):
        copier.configure(delay=60)
        copier.on_closed(source)
        copier.flush()
        assert copier.destination_for(source).exists()


class TestFailures:
    def test_failed_copy_is_reported_remembered_and_retried(self, copier, source, tmp_path, monkeypatch):
        results = []
        copier.add_listener(results.append)
        real_copy = copier.copy
        monkeypatch.setattr(copier, 'copy', lambda path: (_ for _ in ()).throw(PermissionError('locked')))
        copier._run(source, from_timer=False)
        assert not results[0].ok and 'locked' in results[0].error
        assert copier._read_pending() == [str(source)]

        monkeypatch.setattr(copier, 'copy', real_copy)
        copier.retry_pending()
        assert results[-1].ok
        assert copier._read_pending() == []
        assert copier.destination_for(source).exists()

    def test_pending_copy_of_a_file_that_disappeared_is_forgotten(self, copier, source):
        copier._remember_pending(source)
        source.unlink()
        copier.retry_pending()
        assert copier._read_pending() == []

    def test_unknown_parameter_is_refused(self, copier):
        with pytest.raises(TypeError):
            copier.configure(colour='red')
