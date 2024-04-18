import numpy as np
import pytest

from pymodaq.utils import enums


class Enum(enums.BaseEnum):
    name1 = 45
    name2 = 'str'
    name3 = -2


class Enumbis(enums.BaseEnum):
    name4 = 45
    name5 = 'str'
    name6 = -2


def test_base_enum():
    assert Enum.names() == ['name1', 'name2', 'name3']
    txt = 'name2'
    myenum = Enum[txt]
    assert myenum == txt
    assert myenum == Enum['name2']
    assert myenum != 'name1'

    assert Enum.values() == [45, 'str', -2]


def test_enum_checker():
    txt = 'name2'
    myenum = Enum[txt]
    assert isinstance(enums.enum_checker(Enum, myenum), Enum)
    with pytest.raises(ValueError):
        enums.enum_checker(Enum, 'name4')
    assert isinstance(enums.enum_checker(Enum, 'NAME2'), Enum)


def test_enum_to_dict():

    assert Enum.to_dict() == {'name1': 45, 'name2': 'str', 'name3': -2}
    assert Enumbis.to_dict() == {'name4': 45, 'name5': 'str', 'name6': -2}
