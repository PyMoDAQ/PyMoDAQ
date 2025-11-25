# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""
from typing import Callable, Union
from abc import ABCMeta, abstractmethod

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


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


class ObjectFactory(metaclass=ABCMeta):
    """Generic ObjectFactory with a decorator register to add object builders to the factory with a
    unique key identifier

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
            if cls.__name__ not in cls._builders:
                cls._builders[cls.__name__] = {}
            if key not in cls._builders[cls.__name__]:
                cls._builders[cls.__name__][key] = wrapped_class
            else:
                logger.warning(f'The {cls.__name__}/{key} builder is already registered. Replacing it')
            return wrapped_class
        return inner_wrapper

    @property
    def builders(self):
        return self._builders

    def keys_function(self, do_sort=True):
        if do_sort:
            return self.keys
        else:
            return list(self.builders[self.__class__.__name__].keys())

    @property
    def keys(self):
        return sorted(list(self.builders[self.__class__.__name__].keys()))

    @classmethod
    def create(cls, key, **kwargs):
        builder = cls._builders[cls.__name__].get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)

    @classmethod
    def get_class(cls, key):
        return cls._builders[cls.__name__].get(key)
