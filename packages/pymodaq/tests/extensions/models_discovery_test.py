import dataclasses
import sys
import textwrap

import pytest

from pymodaq.extensions.data_mixer import model as data_mixer_model
from pymodaq.extensions.pid import utils as pid_utils


@dataclasses.dataclass
class EntryPoint:
    value: str


@pytest.fixture
def models_package(tmp_path, monkeypatch):
    """A plugin package whose models derive from an intermediate base class of their own"""
    models = tmp_path / 'pymodaq_plugins_fakemodels' / 'models'
    models.mkdir(parents=True)
    (tmp_path / 'pymodaq_plugins_fakemodels' / '__init__.py').write_text('')
    (models / '__init__.py').write_text('')
    (models / 'pid_model.py').write_text(textwrap.dedent('''
        from pymodaq.extensions.pid.utils import PIDModelGeneric

        class MyBase(PIDModelGeneric):
            pass

        class FakePID(MyBase):
            pass
    '''))
    (models / 'mixer_model.py').write_text(textwrap.dedent('''
        from pymodaq.extensions.data_mixer.model import DataMixerModel

        class FakeMixer(DataMixerModel):
            pass
    '''))
    monkeypatch.syspath_prepend(str(tmp_path))
    yield 'pymodaq_plugins_fakemodels'
    for name in [n for n in sys.modules if n.startswith('pymodaq_plugins_fakemodels')]:
        del sys.modules[name]


def test_pid_models_accept_subclasses(models_package, monkeypatch):
    monkeypatch.setattr(pid_utils, 'get_entrypoints', lambda group: [EntryPoint(models_package)]
                        if group == 'pymodaq.models' else [])
    found = {model['name']: model['class'].__name__ for model in pid_utils.get_models()}
    assert found['pid_model'] == 'FakePID'  # the class that derives from your own base is the model, not the base
    assert 'mixer_model' not in found
    assert all(klass != 'PIDModelGeneric' for klass in found.values())


def test_data_mixer_models_accept_subclasses(models_package, monkeypatch):
    monkeypatch.setattr(data_mixer_model, 'get_entrypoints', lambda group: [EntryPoint(models_package)]
                        if group == 'pymodaq.models' else [])
    found = {model['name']: model['class'].__name__ for model in data_mixer_model.get_models()}
    assert found['mixer_model'] == 'FakeMixer'
    assert 'pid_model' not in found
