"""The sources of ontology terms provided: one module per source type, each registering itself with the
:class:`~pymodaq_ontology.source_factory.SourceFactory`. All the modules of this folder are imported."""
from importlib import import_module
import pkgutil

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

for module_info in pkgutil.iter_modules(__path__):
    try:
        import_module(f'{__name__}.{module_info.name}')
    except Exception as e:
        logger.warning(f'Could not import the ontology source module {module_info.name}: {e}')
