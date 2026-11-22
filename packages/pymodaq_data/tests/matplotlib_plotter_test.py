import numpy as np
import pytest

matplotlib = pytest.importorskip('matplotlib')  # optional dependency of pymodaq_data, in the dev extras
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba

from pymodaq_data.data import Axis, DataRaw
from pymodaq_data.plotting.plotter.plotters.matplotlib_plotters import PLOT_COLORS

N_POINTS = 11
ERROR = 0.5
ALPHA = 0.3


@pytest.fixture
def data_with_errors() -> DataRaw:
    axis = Axis('x', 'nm', data=np.linspace(0, 10, N_POINTS), index=0)
    dwa = DataRaw('data', data=[np.ones(N_POINTS), 2 * np.ones(N_POINTS)], axes=[axis], labels=['ch0', 'ch1'])
    dwa.errors = [np.full(N_POINTS, ERROR), np.full(N_POINTS, ERROR)]
    yield dwa
    plt.close('all')


def test_plot1D_with_errors_draws_a_band_of_the_data_color(data_with_errors):
    data_with_errors.plot('matplotlib')
    ax = plt.gca()
    bands = [child for child in ax.get_children() if isinstance(child, PolyCollection)]
    assert len(bands) == len(data_with_errors)
    for ind, (line, band) in enumerate(zip(ax.get_lines(), bands)):
        assert to_rgba(line.get_color()) == to_rgba(PLOT_COLORS[ind])
        assert tuple(band.get_facecolor()[0]) == pytest.approx(to_rgba(PLOT_COLORS[ind], ALPHA))
        vertices = band.get_paths()[0].vertices[:, 1]
        assert vertices.min() == pytest.approx(data_with_errors[ind].min() - ERROR)
        assert vertices.max() == pytest.approx(data_with_errors[ind].max() + ERROR)


def test_plot1D_with_errors_and_a_format(data_with_errors):
    data_with_errors.plot('matplotlib', 'o')  # the format is for the lines only
    assert plt.gca().get_lines()[0].get_marker() == 'o'
