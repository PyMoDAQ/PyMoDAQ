import random

import numpy as np
import pytest

from pymodaq_data.plotting.utils import PlotColors


class TestPlotColor:

    def test_iterable(self):
        with pytest.raises(TypeError):
            pcolor = PlotColors((0, 0, 0))

    def test_get_item(self):
        pcolor = PlotColors()

        for _ in range(10):
            item = random.randrange(100)
            color = pcolor[item]

    def test_len(self):
        N = random.randrange(10) + 1
        pcolor = PlotColors([(0, 0, 0) for _ in range(N)])
        assert len(pcolor) == N

    def test_iter(self):
        pcolor = PlotColors()

        np.array(pcolor)
        colors = [color for color in pcolor]
