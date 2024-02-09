# Standard imports
import typing
from abc import ABCMeta, abstractmethod
from importlib import import_module
from pathlib import Path
from typing import Callable, List

# 3rd party imports
import numpy as np

# project imports
from pymodaq.utils.abstract import abstract_attribute
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq.utils.factory import ObjectFactory

if typing.TYPE_CHECKING:
    from pymodaq.utils.data import DataWithAxes, DataDim

logger = set_logger(get_module_name(__file__))


def register_plotter(parent_module_name: str = 'pymodaq.utils.plotting.data_viewers'):
    plotters = []
    try:
        exporter_module = import_module(f'{parent_module_name}.plotters')

        exporter_path = Path(exporter_module.__path__[0])

        for file in exporter_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    plotters.append(import_module(f'.{file.stem}', exporter_module.__name__))
                except ModuleNotFoundError:
                    pass
    except ModuleNotFoundError:
        pass
    finally:
        return plotters


class PlotterBase(metaclass=ABCMeta):
    """Base class for a plotter. """

    backend: str = abstract_attribute()
    data_dim: str = abstract_attribute()

    def __init__(self):
        """Abstract Exporter Constructor"""
        pass

    @abstractmethod
    def plot(self, data) -> None:
        """Abstract method to plot data object with a given backend"""
        pass


class PlotterFactory(ObjectFactory):
    """Factory class registering and storing Scanners"""

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new plotter class using its 2 identifiers: backend and
        data_dim
        """
        def inner_wrapper(wrapped_class: PlotterBase) -> Callable:
            if cls.__name__ not in cls._builders:
                cls._builders[cls.__name__] = {}
            key = wrapped_class.backend
            sub_key = wrapped_class.data_dim

            if key not in cls._builders[cls.__name__]:
                cls._builders[cls.__name__][key] = {}
            if sub_key not in cls._builders[cls.__name__][key]:
                cls._builders[cls.__name__][key][sub_key] = wrapped_class
            else:
                logger.warning(f'The {cls.__name__}/{key}/{sub_key} builder is already registered.'
                               f' Replacing it')
            return wrapped_class

        return inner_wrapper

    @classmethod
    def create(cls, key, sub_key, **kwargs) -> PlotterBase:
        builder = cls._builders[cls.__name__].get(key).get(sub_key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)

    def get(self, backend: str, data_dim: str, **kwargs):
        return self.create(backend, data_dim, **kwargs)

    def backends(self) -> List[str]:
        """Returns the list of plotter backends, main identifier of a given plotter"""
        return sorted(list(self.builders[self.__class__.__name__].keys()))

    def data_dims(self, backend: str) -> List[str]:
        """Returns the list of data_dim for a given backend"""
        return list(self.builders[self.__class__.__name__][backend].keys())


plotter_factory = PlotterFactory()
register_plotter()
