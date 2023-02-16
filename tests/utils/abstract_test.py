# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import pytest

from pymodaq.utils.abstract import ABCMeta, abstract_attribute


class AbstractFoo(metaclass=ABCMeta):
    @abstract_attribute
    def bar(self):
        pass


class Foo(AbstractFoo):
    def __init__(self):
        self.bar = 3


class BadFoo(AbstractFoo):
    def __init__(self):
        pass


class Base(metaclass=ABCMeta):
    aa = abstract_attribute()


class RealClass(Base):
    aa = 'mandatory_attribute'


class RealBadClass(Base):
    ...


def test_abstract_attribute():
    Foo()  # ok
    with pytest.raises(NotImplementedError):
        BadFoo()


def test_abstract_class_attribute():

    RealClass()

    with pytest.raises(NotImplementedError):
        s = RealBadClass()
