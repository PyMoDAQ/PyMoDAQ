from enum import Enum
from pymodaq.utils.daq_utils import find_index
from pymodaq.utils.math_utils import my_moment
import numpy as np
from scipy.optimize import curve_fit
from typing import List, Union


class BaseEnum(Enum):
    """Enum to be used within pymodaq with some utility methods"""

    @classmethod
    def names(cls) -> List[str]:
        """Returns all the names of the enum"""
        return list(cls.__members__.keys())

    def __eq__(self, other: Union[str, Enum]):
        """testing for equality using the enum name"""
        if isinstance(other, str):
            if other == self.name:
                return True
        return super().__eq__(other)

    def enforcer(self, item):

        if item is None:
            raise ValueError(f'{item} is an invalid {self.__class__.__name__}. Should be a'
                             f' {self.__class__.__name__} enum or '
                             f'a string in'
                             f' {self.__class__.names()}')

        if not isinstance(item, self.__class__):
            if item in self.__class__.names():
                item = self.__class__[item]
            else:
                raise ValueError(f'{item} is an invalid {self.__class__.__name__}. Should be a'
                                 f' {self.__class__.__name__} enum or '
                                 f'a string in'
                                 f' { self.__class__.names()}')

        return item


