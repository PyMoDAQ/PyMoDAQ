from abc import ABCMeta, abstractmethod
from typing import Callable
from enum import StrEnum

from numpy.random import RandomState


from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class LossDim(StrEnum):

    LOSS_1D = 'Loss1D'
    LOSS_2D = 'Loss2D'
    LOSS_ND = 'LossND'

    def get_enum_from_dim_as_int(self, dim: int):
        if dim == 1:
            return LossDim.LOSS_1D
        elif dim == 2:
            return LossDim.LOSS_2D
        elif dim > 2:
            return LossDim.LOSS_ND
        else:
            raise ValueError(f'No Loss with dim={dim} is known')


class LossFunctionBase(metaclass=ABCMeta):
    _loss : Callable
    dim: LossDim
    usual_name : str
    params : property(abstractmethod)

    def __call__(self, *args, **kwargs):
        return self._loss(*args, **kwargs)


class LossFunctionFactory:
    _builders = {}

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new scanner class using its 2 identifiers: scan_type and scan_sub_type
        """

        def inner_wrapper(wrapped_class: LossFunctionBase) -> Callable:
            key = wrapped_class.usual_name
            dim = wrapped_class.dim
            if dim not in cls._builders:
                cls._builders[dim] = {}
            if key not in cls._builders[dim]:
                cls._builders[dim][key] = wrapped_class
            else:
                logger.warning(f'The {key} builder is already registered. Replacing it')
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get(cls, dim: LossDim, key : str) -> LossFunctionBase:
        builder = cls._builders.get(dim).get(key)
        if not builder:
            raise ValueError(f'Unknown Loss function with dim={dim} and key={key}')
        return builder

    @classmethod
    def create(cls, dim: LossDim, key: str, **kwargs) -> LossFunctionBase:
        return cls.get(dim, key)(**kwargs)

    @classmethod
    def dims(cls) -> list[LossDim]:
        return list(cls._builders.keys())

    @classmethod
    def keys(cls, dim: LossDim) -> list[str]:
            return list(cls._builders.get(dim).keys())
