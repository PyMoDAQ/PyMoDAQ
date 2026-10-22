from qtpy import QtWidgets

from pytest import mark
from pymodaq.dashboard import extensions
from pymodaq.utils.plugin_testing import loaded_extension


class TestExtensions:
    @mark.parametrize('ext_name', list(extensions))
    def test_load(self, ext_name):
        with loaded_extension(extensions[ext_name].klass) as (dashboard, ext):
            QtWidgets.QApplication.processEvents()

    @mark.parametrize('ext_name', list(extensions))
    def test_load_with_an_experiment_applied(self, ext_name, monkeypatch):
        """ As when the extension is opened from a Dashboard where an experiment is loaded: the experiment hook is
        then called right after the UI is set up"""
        from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
        monkeypatch.setattr(ExperimentManager, 'entry_applied', property(lambda self: True, lambda self, value: None))
        with loaded_extension(extensions[ext_name].klass) as (dashboard, ext):
            QtWidgets.QApplication.processEvents()
