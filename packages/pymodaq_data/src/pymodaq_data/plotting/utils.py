import copy
from typing import Iterable as IterableType, Iterable

from pymodaq_utils.utils import config


class PlotColors:

    def __init__(self, colors=config('data', 'plotting', 'plot_colors')[:]):

        self._internal_counter = -1

        self.check_colors(colors)
        self._plot_colors = [tuple(color) for color in colors]

    def copy(self):
        return copy.copy(self)

    def remove(self, item):
        self._plot_colors.remove(item)

    def __getitem__(self, item: int):
        if not isinstance(item, int):
            raise TypeError('getter should be an integer')
        return tuple(self._plot_colors[item % len(self._plot_colors)])

    def __len__(self):
        return len(self._plot_colors)

    def __iter__(self):
        self._internal_counter = -1
        return self

    def __next__(self):
        if self._internal_counter >= len(self) - 1:
            raise StopIteration
        self._internal_counter += 1
        return self[self._internal_counter]

    def check_colors(self, colors: IterableType):
        if not isinstance(colors, Iterable):
            raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')
        for color in colors:
            self.check_color(color)

    @staticmethod
    def check_color(color: IterableType):
        if not isinstance(color, Iterable) and len(color) != 3:
            raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')
        # for col_val in color:
        #     if not (isinstance(col_val, int) and 0 <= col_val <= 255):
        #         raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')
