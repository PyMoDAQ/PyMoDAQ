import numpy as np
import pytest

from pymodaq_data.h5modules import backends, saving
from pymodaq_data.h5modules.data_saving import DataSaverLoader
from pymodaq_data import data as data_mod

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(params=tested_backend)
def h5saver_lowlevel(request, tmp_path):
    """H5SaverLowLevel on a fresh empty file, parametrized over available backends."""
    h5saver = saving.H5SaverLowLevel(backend=request.param)
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, new_file=True)
    yield h5saver
    h5saver.close_file()


@pytest.fixture(scope="session", params=tested_backend)
def h5file_with_data(request, tmp_path_factory):
    """Session-scoped: writes a pre-populated HDF5 file once per backend.
    Returns (path, backend) so consumers can open it with the matching backend."""
    backend = request.param
    fn = tmp_path_factory.mktemp("data") / 'mydata.h5'
    h5saver = saving.H5SaverLowLevel(backend=backend)
    h5saver.init_file(fn, new_file=True)
    data_array = np.arange(0, 5 * 6).reshape((5, 6)).astype(float)
    dwa = data_mod.DataWithAxes('myData', data_mod.DataSource['raw'], data=[data_array])
    dwa.create_missing_axes()
    DataSaverLoader(h5saver).add_data('/RawData', dwa)
    h5saver.close_file()
    return fn, backend


@pytest.fixture
def h5saver_with_data(h5file_with_data):
    """H5SaverLowLevel opened on the pre-populated file from h5file_with_data."""
    path, backend = h5file_with_data
    h5saver = saving.H5SaverLowLevel(backend=backend)
    h5saver.init_file(path)
    yield h5saver
    h5saver.close_file()
