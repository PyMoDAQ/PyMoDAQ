from qtpy import QtWidgets

from pytest import mark
from pymodaq.dashboard import extensions
from pymodaq.utils.plugin_testing import loaded_extension


class TestExtensions:
    @mark.parametrize('ext_name', list(extensions))
    def test_load(self, ext_name):
        with loaded_extension(extensions[ext_name].klass) as (dashboard, ext):
            QtWidgets.QApplication.processEvents()
