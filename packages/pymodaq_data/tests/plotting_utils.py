import random

import numpy as np
import pytest


class TestPlotColor:

    def test_iterable(self):
        with pytest.raises(TypeError):
            pcolor = pymodaq_data.plotting.utils.PlotColors((0, 0, 0))

    def test_non_integer(self):
        with pytest.raises(TypeError):
            pcolor = pymodaq_data.plotting.utils.PlotColors([(0, 0., 0)])

    def test_non_8bits(self):
        with pytest.raises(TypeError):
            pcolor = pymodaq_data.plotting.utils.PlotColors([(0, 256, 0)])

    def test_negative(self):
        with pytest.raises(TypeError):
            pcolor = pymodaq_data.plotting.utils.PlotColors([(0, -5, 0)])

    def test_get_item(self):
        pcolor = pymodaq_data.plotting.utils.PlotColors()

        for _ in range(10):
            item = random.randrange(100)
            color = pcolor[item]

    def test_len(self):
        N = random.randrange(10) + 1
        pcolor = pymodaq_data.plotting.utils.PlotColors([(0, 0, 0) for _ in range(N)])
        assert len(pcolor) == N

    def test_iter(self):
        pcolor = pymodaq_data.plotting.utils.PlotColors()

        np.array(pcolor)
        colors = [color for color in pcolor]
