import importlib.metadata as metadata

from pymodaq_gui.managers.manager_base import ManagerBase

from pymodaq.utils.managers import extra_managers
from pymodaq.utils.managers.extra_managers import get_extra_managers


class DummyManager(ManagerBase):
    entry_type = 'dummy'
    entry_extension = '.dummy'
    icon_name = 'select'


class NotAManager:
    pass


def entry_point(name, value):
    return metadata.EntryPoint(name=name, value=value, group='pymodaq.managers')


class TestGetExtraManagers:
    def test_no_entry_point(self, monkeypatch):
        monkeypatch.setattr(extra_managers, 'get_entrypoints', lambda group: [])
        assert get_extra_managers() == {}

    def test_valid_manager_is_found_by_entry_point_name(self, monkeypatch):
        eps = [entry_point('dummy', f'{__name__}:DummyManager')]
        monkeypatch.setattr(extra_managers, 'get_entrypoints', lambda group: eps)
        assert get_extra_managers() == {'dummy': DummyManager}

    def test_broken_and_invalid_managers_are_skipped(self, monkeypatch):
        eps = [entry_point('missing', 'no_such_module_for_managers:Manager'),
               entry_point('invalid', f'{__name__}:NotAManager'),
               entry_point('dummy', f'{__name__}:DummyManager')]
        monkeypatch.setattr(extra_managers, 'get_entrypoints', lambda group: eps)
        assert get_extra_managers() == {'dummy': DummyManager}
