

from pymodaq.utils import h5modules
from pymodaq.utils.h5modules import exporter as h5export
from pymodaq.utils.h5modules.utils import register_exporter, register_exporters



class TestH5Exporter:

    def test_exporters_registry(self):
        factory = h5export.ExporterFactory()

        for ext in factory.exporters_registry.keys():
            assert ext in ('h5', 'txt', 'npy')


        #todo add a test to check this but knowing that some may be missing (for instance hyperspy if no hyperspy package)
        # assert factory.get_file_filters() == \
        #        "Single node h5 file (*.h5);;" \
        #        "Text files (*.txt);;" \
        #        "Ascii file (*.ascii);;" \
        #        "Binary NumPy format (*.npy);;" \
        #        "Hyperspy file format (*.hspy)"


def test_register_exporter():

    exporter_modules = register_exporter('pymodaq.utils.h5modules')
    assert len(exporter_modules) >= 1  # this is the base exporter module

    assert 'h5' in h5export.ExporterFactory.exporters_registry
    assert 'txt' in h5export.ExporterFactory.exporters_registry
    assert 'npy' in h5export.ExporterFactory.exporters_registry


def test_register_exporter_mock_examples():

    exporter_modules = register_exporter('pymodaq_plugins_mockexamples')
    assert len(exporter_modules) >= 1  # this is the base exporter module
    assert len(h5export.ExporterFactory.exporters_registry['txt']) >= 2


