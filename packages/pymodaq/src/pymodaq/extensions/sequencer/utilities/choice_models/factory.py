from importlib import import_module
from pathlib import Path
from typing import Callable

from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
from pymodaq_utils.logger import set_logger, get_module_name


logger = set_logger(get_module_name(__file__))


def register_choice_models(parent_module_name: str = 'pymodaq_plugins_sequencer.utilities.choice_models'):
    models = []
    try:
        models_module = import_module(f'{parent_module_name}.models')

        model_path = Path(models_module.__path__[0])

        for file in model_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    models.append(import_module(f'.{file.stem}',
                                                  models_module.__name__))
                except Exception as e:
                    logger.warning(str(e))
    except Exception as e:
        logger.warning(str(e))
    finally:
        return models


class ChoiceModelFactory:
    """The factory class to get Sequencer Elements"""

    models_registry = {}

    @classmethod
    def register_choice(cls) -> Callable:
        """Class decorator method to register Models to be used with the Choice Element class
        to the internal registry.
        Must be used as a decorator above the definition of a ChoiceModelBase inherited class.

        The class must implement the ChoiceModelBase interface
        """

        def inner_wrapper(wrapped_class: type[ChoiceModelBase]) -> type[ChoiceModelBase]:
            model_name = wrapped_class.model_name

            if model_name not in cls.models_registry:
                cls.models_registry[model_name] = wrapped_class
            else:
                logger.info(f"Model {model_name} already registered")
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def get_model(cls, name: str) -> type[ChoiceModelBase]:
        """Factory command to get registered subentry handler.

        This method gets the appropriate executor class from the registry
        """

        if name not in cls.models_registry:
            raise KeyError(f"{name} is not a supported element.")

        return cls.models_registry[name]

    @property
    def models(self) -> list[str]:
        return [model for model in self.models_registry.keys()]


