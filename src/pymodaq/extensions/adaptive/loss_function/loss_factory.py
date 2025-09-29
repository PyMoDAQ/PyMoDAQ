from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from typing import Callable, Type, Union, Sequence
from pymodaq_utils.enums import StrEnum


from adaptive.learner import Learner1D, Learner2D, LearnerND, BaseLearner


from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class LossDim(StrEnum):

    LOSS_1D = 'Loss1D'
    LOSS_2D = 'Loss2D'
    LOSS_ND = 'LossND'

    @staticmethod
    def get_enum_from_dim_as_int(dim: int):
        if dim == 1:
            return LossDim.LOSS_1D
        elif dim == 2:
            return LossDim.LOSS_2D
        elif dim > 2:
            return LossDim.LOSS_ND
        else:
            raise ValueError(f'No Loss with dim={dim} is known')

    def get_learner_from_enum(self, bounds: OrderedDict[str, tuple[float, float]],
                              loss_function: 'LossFunctionBase') -> Union[Learner1D, Learner2D, LearnerND]:
        """ Return an instance of a Learner given the enum value

        Parameters
        ----------
        bounds: type depends on the learner, could be a tuple of real numbers (Learner1D) or a tuple of tuples of real
            numbers
        loss_function: one of the LossFunction class as given by the LossFunctinoFactory

        See Also:
        ---------
        :class:`LossFunctionFactory`
        """
        if self == self.LOSS_1D:
            bounds = bounds.popitem(last=False)[1]
            return Learner1D(None, bounds, loss_per_interval=loss_function)
        elif self == self.LOSS_2D:
            return Learner2D(None, tuple(bounds.values()), loss_per_triangle=loss_function)
        elif self == self.LOSS_ND:
            return LearnerND(None, tuple(bounds.values()), loss_per_simplex=loss_function)
        else:
            raise ValueError(f'No learner for this enum: {self}')


class LossFunctionBase(metaclass=ABCMeta):
    _loss : Callable
    dim: LossDim
    usual_name: str
    params: list[dict] = []

    def __call__(self, *args, **kwargs):
        return self._loss(**kwargs)


class LossFunctionFactory:
    _builders = {}

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new LossFunction class using its 2 identifiers: LossDim and usual_name
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
    def get(cls, dim: LossDim, key : str) -> Type[LossFunctionBase]:
        loss = cls._builders.get(dim, {key: None}).get(key)
        if loss is None:
            raise ValueError(f'Unknown Loss function with dim={dim} and key={key}')
        return loss

    @classmethod
    def create(cls, dim: LossDim, key: str, **kwargs) -> LossFunctionBase:
        return cls.get(dim, key)()(**kwargs)

    @classmethod
    def dims(cls) -> list[LossDim]:
        return list(cls._builders.keys())

    @classmethod
    def keys(cls, dim: LossDim) -> list[str]:
        try:
            return list(cls._builders.get(dim).keys())
        except (AttributeError, ValueError, KeyError) as e:
            return []
