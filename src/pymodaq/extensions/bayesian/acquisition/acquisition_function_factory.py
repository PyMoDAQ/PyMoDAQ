from abc import ABCMeta, abstractmethod
from typing import Callable

from numpy.random import RandomState
from bayes_opt.acquisition import AcquisitionFunction

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class GenericAcquisitionFunctionBase(metaclass=ABCMeta):
    _function: AcquisitionFunction
    usual_name: str
    short_name: str
    params : property(abstractmethod)

    def base_acq(self, mean, std):
        return self._function.base_acq(mean, std)

    def decay_exploration(self):
        self._function.decay_exploration()

    @property
    def tradeoff(self):
        raise NotImplementedError

    @tradeoff.setter
    def tradeoff(self, tradeoff):
        raise NotImplementedError

    def suggest(self, gaussian_process, target_space, n_random = 1000, n_l_bfgs_b = 10, fit_gp = True):
        return self._function.suggest(gaussian_process, target_space, n_random, n_l_bfgs_b, fit_gp)
    

class GenericAcquisitionFunctionFactory:
    _builders = {}

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new scanner class using its 2 identifiers: scan_type and scan_sub_type
        """

        def inner_wrapper(wrapped_class: GenericAcquisitionFunctionBase) -> Callable:
            key = wrapped_class.short_name

            if key not in cls._builders:
                cls._builders[key] = wrapped_class
            else:
                logger.warning(f'The {key} builder is already registered. Replacing it')
            return wrapped_class

        return inner_wrapper


    @classmethod
    def get(cls, key : str) -> GenericAcquisitionFunctionBase:
        builder = cls._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder

    @classmethod
    def create(cls, key, **kwargs) -> GenericAcquisitionFunctionBase:
        return cls._builders.get(key)(**kwargs)

    @classmethod
    def keys(cls) -> list[str]:
        return list(cls._builders.keys())

    @classmethod
    def short_names(cls) -> list[str]:
        return list(cls.keys())

    @classmethod
    def usual_names(cls) -> list[str]:
        return [cls.get(builder).usual_name for builder in cls._builders]
