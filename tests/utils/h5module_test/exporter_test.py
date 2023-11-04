import numpy as np
from pathlib import Path
import pytest

from pymodaq.utils.h5modules.saving import H5SaverLowLevel
from pymodaq.utils import data as data_mod
from pymodaq.utils.h5modules.data_saving import DataSaverLoader, AxisSaverLoader

from pymodaq.utils.h5modules import exporter as h5export
from pymodaq.utils.h5modules.utils import register_exporter, register_exporters


LABEL = 'A Label'
UNITS = 'units'
OFFSET = -20.4
SCALING = 0.22
SIZE = 20
DATA = OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE)

DATA0D = np.array([2.7])
DATA1D = np.arange(0, 10)
DATA2D = np.arange(0, 5*6).reshape((5, 6))
DATAND = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))
Nn0 = 10
Nn1 = 5


def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData', source=data_mod.DataSource['raw'],
              labels=None) -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    dwa = data_mod.DataWithAxes(name, source, data=[data for ind in range(Ndata)],
                                axes=axes, labels=labels)
    if len(axes) == 0:
        dwa.create_missing_axes()
    return dwa


@pytest.fixture(scope="session")
def create_data(tmp_path_factory) -> Path:
    fn = tmp_path_factory.mktemp("data") / 'mydata.h5'
    h5saver = H5SaverLowLevel()
    h5saver.init_file(fn, new_file=True)
    datasaver = DataSaverLoader(h5saver)

    dwa = init_data()
    datasaver.add_data('/RawData', dwa)
    h5saver.close_file()
    return fn


@pytest.fixture
def get_h5saver(create_data):
    path = create_data
    h5saver = H5SaverLowLevel()
    h5saver.init_file(path)
    yield h5saver
    h5saver.close_file()


class TestH5Exporter:

    def test_exporters_registry(self):
        factory = h5export.ExporterFactory()

        for ext in ('h5', 'txt', 'npy'):
            assert ext in list(factory.exporters_registry.keys())


def test_register_exporter():

    exporter_modules = register_exporter('pymodaq.utils.h5modules')
    assert len(exporter_modules) >= 1  # this is the base exporter module

    assert 'h5' in h5export.ExporterFactory.exporters_registry
    assert 'txt' in h5export.ExporterFactory.exporters_registry
    assert 'npy' in h5export.ExporterFactory.exporters_registry


def test_txt_exporter(get_h5saver, tmp_path):

    h5saver = get_h5saver
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


def test_npy_exporter(get_h5saver, tmp_path):

    h5saver = get_h5saver
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
