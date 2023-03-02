
from pymodaq.utils import h5modules
from pymodaq.utils.h5modules import exporter as h5export


#Unused import only needed to update the registry
from pymodaq.utils.h5modules.exporters.base import H5h5Exporter, H5txtExporter, H5npyExporter
from pymodaq.utils.h5modules.exporters.flimj import H5asciiExporter


class TestH5Exporter:

    def test_exporters_registry(self):
        factory = h5export.ExporterFactory()

        for ext in factory.exporters_registry.keys():
            assert ext in ('h5', 'txt', 'ascii', 'npy', 'hspy')

        #todo add a test to check this but knowing that some may be missing (for instance hyperspy if no hyperspy package)
        # assert factory.get_file_filters() == \
        #        "Single node h5 file (*.h5);;" \
        #        "Text files (*.txt);;" \
        #        "Ascii file (*.ascii);;" \
        #        "Binary NumPy format (*.npy);;" \
        #        "Hyperspy file format (*.hspy)"

    def test_exporter_creation(self):

        assert isinstance(h5export.ExporterFactory.create_exporter('txt'), H5txtExporter)
        assert isinstance(h5export.ExporterFactory.create_exporter('ascii'), H5asciiExporter)
        assert isinstance(h5export.ExporterFactory.create_exporter('h5'), H5h5Exporter)
        assert isinstance(h5export.ExporterFactory.create_exporter('npy'), H5npyExporter)
