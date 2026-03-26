import numpy as np
import pytest

from pymodaq_data.h5modules.data_saving import DataSaverLoader, AxisSaverLoader
from pymodaq_data.h5modules import exporter as h5export
from pymodaq_data.h5modules.utils import register_exporter, register_exporters


class TestH5Exporter:

    def test_exporters_registry(self):
        factory = h5export.ExporterFactory()

        for ext in ('h5', 'txt', 'npy'):
            assert ext in list(factory.exporters_registry.keys())


def test_register_exporter():

    exporter_modules = register_exporter('pymodaq_data.h5modules')
    assert len(exporter_modules) >= 1  # this is the base exporter module

    assert 'h5' in h5export.ExporterFactory.exporters_registry
    assert 'txt' in h5export.ExporterFactory.exporters_registry
    assert 'npy' in h5export.ExporterFactory.exporters_registry


def test_txt_exporter(h5saver_with_data, tmp_path):

    h5saver = h5saver_with_data
    dataloader = DataSaverLoader(h5saver)
    axis_loader = AxisSaverLoader(h5saver)
    dwa = dataloader.load_data('/RawData/Data00')

    exporter = h5export.ExporterFactory.create_exporter('txt', 'Text files')

    #exporting 2D data as txt
    file_path = tmp_path.joinpath('exported_data.txt')
    exporter.export_data(h5saver.get_node('/RawData/Data00'), file_path)
    assert np.allclose(np.loadtxt(file_path), dwa[0])

    # exporting 1D data as txt
    file_path = tmp_path.joinpath('exported_axis.txt')
    exporter.export_data(h5saver.get_node('/RawData/Axis00'), file_path)
    assert np.allclose(np.loadtxt(file_path), axis_loader.load_axis('/RawData/Axis00').get_data())


def test_npy_exporter(h5saver_with_data, tmp_path):

    h5saver = h5saver_with_data
    dataloader = DataSaverLoader(h5saver)
    axis_loader = AxisSaverLoader(h5saver)
    dwa = dataloader.load_data('/RawData/Data00')
    axis = axis_loader.load_axis('/RawData/Axis00')
    exporter = h5export.ExporterFactory.create_exporter('npy', 'Binary NumPy format')

    #exporting 2D data as npy
    file_path = tmp_path.joinpath('exported_data.npy')
    exporter.export_data(h5saver.get_node('/RawData/Data00'), file_path)
    assert np.allclose(np.load(file_path), dwa[0])

    # exporting 1D data as npy
    file_path = tmp_path.joinpath('exported_axis.npy')
    exporter.export_data(h5saver.get_node('/RawData/Axis00'), file_path)
    assert np.allclose(np.load(file_path), axis.get_data())
