# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""
from typing import Callable, Union
from abc import ABCMeta, abstractmethod


class BuilderBase(ABCMeta):
    """Abstract class defining an object/service builder with a callable interface accepting some arguments

    See https://realpython.com/factory-method-python/ for some details

    See Also
    --------
    pymodaq.post_treatment.process_1d_to_scalar
    """
    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class ObjectFactory:
    """Generic ObjectFactory with a decorator register to add object builders to the factory with a unique key
    identifier

    See https://realpython.com/factory-method-python/ for some details

    Examples
    --------
    @ObjectFactory.register('custom')
    def my_custom_builder():
        pass

    See Also
    --------
    pymodaq.post_treatment.process_1d_to_scalar.Data1DProcessorFactory
    """
    _builders = {}

    @classmethod
    def register(cls, key: str) -> Callable:
        def inner_wrapper(wrapped_class: Union[BuilderBase, Callable]) -> Callable:
            if key in cls._builders:
                pass
            cls._builders[key] = wrapped_class
            return wrapped_class
        return inner_wrapper

    @property
    def builders(self):
        return self._builders

    @classmethod
    def create(cls, key, **kwargs):
        builder = cls._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)

