# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber

Introduce some nice ABCMeta class allowing that a particular attribute has been declared when instantiating
See https://stackoverflow.com/a/50381071/8090831
"""

from abc import ABCMeta as NativeABCMeta
from abc import abstractmethod
from typing import cast, Any, Callable, TypeVar


R = TypeVar('R')


class DummyAttribute:
    pass


def abstract_attribute(obj: Callable[[Any], R] = None) -> R:
    _obj = cast(Any, obj)
    if obj is None:
        _obj = DummyAttribute()
    _obj.__is_abstract_attribute__ = True
    return cast(R, _obj)


class ABCMeta(NativeABCMeta):

    def __call__(cls, *args, **kwargs):
        instance = NativeABCMeta.__call__(cls, *args, **kwargs)
        abstract_attributes = {
            name
            for name in dir(instance)
            if getattr(getattr(instance, name), '__is_abstract_attribute__', False)
        }
        if abstract_attributes:
            raise NotImplementedError(
                "Can't instantiate abstract class {} with"
                " abstract attributes: {}".format(
                    cls.__name__,
                    ', '.join(abstract_attributes)
                )
            )
        return instance
