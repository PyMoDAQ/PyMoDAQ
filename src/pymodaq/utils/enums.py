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

    @classmethod
    def values(cls) -> List[str]:
        """Returns all the names of the enum"""
        return [cls[name].value for name in cls.names()]

    def __eq__(self, other: Union[str, Enum]):
        """testing for equality using the enum name"""
        if isinstance(other, str):
            if other == self.name:
                return True
        return super().__eq__(other)


def enum_checker(enum: BaseEnum, item: Union[BaseEnum, str]):
    """Check if the item parameter is a valid enum or at least one valid string name of the enum

    If a string, transforms it to a valid enum (case not important)

    Parameters
    ----------
    enum: BaseEnum class or one of its derivated class

    item: str or BaseEnum instance

    Returns
    -------
    BaseEnum class or one of its derivated class
    """

    if not isinstance(item, enum):
        if not isinstance(item, str):
            raise ValueError(f'{item} is an invalid {enum}. Should be a {enum} enum or '
                             f'a string in {enum.names()}')
        for ind, name in enumerate(enum.names()):
            if item.lower() == name.lower():
                item = enum[name]
                break
        else:
            raise ValueError(f'{item} is an invalid {enum}. Should be a {enum} enum or '
                             f'a string in {enum.names()}')
    return item



