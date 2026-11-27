"""Base class and factory of the sources of ontology terms

A source reads the terms of an ontology from somewhere (a file, a web address...) in some format. The manager only
asks it for a list of :class:`~pymodaq_ontology.terms.OntologyTerm`. The sources provided are in the sibling folder
``sources``, one module per source type, each registering itself with :meth:`SourceFactory.register`: adding a source
type is adding a file. A plugin can provide other source types and registers them the same way, from a module or a
class named in the ``pymodaq.ontology_sources`` entry point group.
"""
from abc import ABC, abstractmethod
from importlib import import_module

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_entrypoints

from pymodaq_ontology.terms import OntologyTerm

logger = set_logger(get_module_name(__file__))

GROUP = 'pymodaq.ontology_sources'


class OntologySource(ABC):
    """A place where to read the terms of an ontology

    Subclasses define ``source_type`` (the name used to create them) and :meth:`terms`.
    """
    source_type: str = NotImplemented

    def __init__(self, location: str):
        self.location = str(location)

    @property
    def identifier(self) -> str:
        """What identifies the source in the entry files, for instance ``terms:/path/to/file.toml``"""
        return f'{self.source_type}:{self.location}'

    @abstractmethod
    def terms(self) -> list[OntologyTerm]:
        """Read the terms. Raises an exception if the location cannot be read"""


class SourceFactory:
    """Registry of the source types"""
    _types: dict[str, type[OntologySource]] = {}
    _discovered = False

    @classmethod
    def register(cls, source_class: type[OntologySource]) -> type[OntologySource]:
        """Register a source type, to be used as a class decorator"""
        if source_class.source_type is NotImplemented:
            raise NotImplementedError(f'{source_class} does not define source_type')
        cls._types[source_class.source_type] = source_class
        return source_class

    @classmethod
    def _discover(cls) -> None:
        if cls._discovered:
            return
        cls._discovered = True
        import_module('pymodaq_ontology.sources')  # the sources provided register themselves
        for entry_point in get_entrypoints(group=GROUP):
            try:
                loaded = entry_point.load()
            except Exception as e:
                logger.exception(f'Could not load the ontology source {entry_point.name}: {e}')
                continue
            if isinstance(loaded, type) and issubclass(loaded, OntologySource):
                cls.register(loaded)

    @classmethod
    def names(cls) -> list[str]:
        """The names of the source types available"""
        cls._discover()
        return list(cls._types)

    @classmethod
    def get_class(cls, source_type: str) -> type[OntologySource]:
        """The class of a source type"""
        cls._discover()
        try:
            return cls._types[source_type]
        except KeyError:
            raise ValueError(f'Unknown ontology source type "{source_type}", available: {cls.names()}') from None

    @classmethod
    def create(cls, source_type: str, location: str) -> OntologySource:
        cls._discover()
        try:
            return cls._types[source_type](location)
        except KeyError:
            raise ValueError(f'Unknown ontology source type "{source_type}", available: {cls.names()}') from None

    @classmethod
    def from_identifier(cls, identifier: str) -> OntologySource:
        """Create a source from its identifier (``type:location``)"""
        source_type, _, location = identifier.partition(':')
        return cls.create(source_type, location)
