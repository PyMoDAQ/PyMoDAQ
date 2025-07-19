from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from .ui_base import DAQ_Move_UI_Base

logger = set_logger(get_module_name(__file__))



class ActuatorUIFactory:
    _builders: dict[str, type['DAQ_Move_UI_Base']] = {}

    @classmethod
    def register(cls, identifier: str) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new scanner class using its 1 identifier
        """

        def inner_wrapper(wrapped_class: type['DAQ_Move_UI_Base']) -> type['DAQ_Move_UI_Base']:
            key = identifier

            if key not in cls._builders:
                cls._builders[key] = wrapped_class
            else:
                logger.warning(f'The {key} builder is already registered. Replacing it')
            return wrapped_class

        return inner_wrapper


    @classmethod
    def get(cls, key : str) -> type['DAQ_Move_UI_Base']:
        builder = cls._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder

    @classmethod
    def create(cls, key: str, **kwargs) -> 'DAQ_Move_UI_Base':
        return cls._builders[key](**kwargs)

    @classmethod
    def keys(cls) -> list[str]:
        return list(cls._builders.keys())
