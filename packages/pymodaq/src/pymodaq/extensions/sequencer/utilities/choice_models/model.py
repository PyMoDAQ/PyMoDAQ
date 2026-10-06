
import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from serializall import SerializableFactory

from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_data import DataToExport
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils.logger import set_logger, get_module_name



if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase
    from pymodaq.extensions.sequencer.utilities.elements.choice import ChoiceElt

logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()

class ChoiceModelBase(ParameterManager):
    params = []
    model_name: str = abstract_attribute()

    def __init__(self, parent_elt: 'ChoiceElt',):
        super().__init__(settings_name='choice_model_settings',
                         action_list=("search", "save", "update", "load"),
                         )
        self.parent_elt = parent_elt
        self.modules_manager: ModulesManager = parent_elt.modules_manager

    def __eq__(self, other: 'ChoiceModelBase') -> bool:
        return self.to_dict() == other.to_dict()

    def updated_module_manager(self):
        """ called whenever the parent modules manager is updated

        to be reimplemented
        """
        pass

    @property
    def selected(self) -> list[str]:
        return self.modules_manager.selected_detectors_name

    def execute(self, dte: DataToExport):
        pass

    def check_set_is_valid(self):
        """ Check if the current settings of this model are valid

        To be reimplemented

        Should raise ElementError if not valid
        """
        return None

    def to_dict(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this model params

        to be reimplemented
        """
        return {}

    def from_dict(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods

        to be reimplemented
        """
        pass


def get_choice_models():
    """
    Register ChoiceModels in pymodaq models entrypoints

    Returns
    -------
    list: list of dict containing the name and python module of the found models

    Example
    -------
    model = [{'name': 'MyModel', 'class': DataModel}]
    """
    main_model_path = Path(__file__).parent.parent.parent.joinpath('models')
    for mod in pkgutil.iter_modules([str(main_model_path)]):
        try:
            importlib.import_module(f'pymodaq.extensions.sequencer.models.{mod.name}')
            # by just importing the module, the models that may have a register decorator will be
            # added to the factory

        except Exception as e:  # pragma: no cover
            logger.warning(str(e))

    discovered_models = list(get_entrypoints(group='pymodaq.models'))

    if len(discovered_models) > 0:
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        # by just importing the module, the models that may have a register decorator will be
                        # added to the factory

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')


