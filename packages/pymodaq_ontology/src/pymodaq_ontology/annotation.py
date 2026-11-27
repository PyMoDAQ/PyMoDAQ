"""Write the assigned terms in the data to be saved, as the ``semantic_iri`` extra attribute of the arrays"""
from typing import Callable, Optional

from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data.h5modules.data_saving import DataBundle

from pymodaq_ontology.assignment import Assignment
from pymodaq_ontology.channels import Channel
from pymodaq_ontology.terms import ACTUATOR, DETECTOR

logger = set_logger(get_module_name(__file__))

ATTRIBUTE = 'semantic_iri'
EMBEDDED_TEXT = 'excerpt'  # string array holding the text
EMBEDDED_GROUP = 'Ontology'  # read by pymodaq_data.h5modules.representations.embedded_semantics


def annotate_bundle(bundle: DataBundle, assignment: Assignment) -> DataBundle:
    """Add ``semantic_iri`` to each data of the bundle having at least one assigned channel

    The value is one IRI if the same term is assigned to all the arrays of the data, otherwise a list with one IRI
    per array (empty text for an array without term). Only the first bundle of an acquisition is annotated, the
    attributes being written when the arrays are created.
    """
    if bundle.save_index:
        return bundle
    for dwa in bundle.dte.data:
        labels = list(dwa.labels) if getattr(dwa, 'labels', None) else []
        keys = [Channel(module=dwa.origin, kind=DETECTOR, data_name=dwa.name,
                        label=labels[index] if index < len(labels) else f'CH{index:02d}').key
                for index in range(len(dwa.data))]
        iris = [assignment.get(key) or '' for key in keys]
        if not any(iris) and len(iris) == 1:  # an actuator is one channel named after its module
            iris = [assignment.get(Channel(module=dwa.origin, kind=ACTUATOR).key) or '']
        if any(iris):
            dwa.add_extra_attribute(**{ATTRIBUTE: iris[0] if len(set(iris)) == 1 else iris})
    return bundle


def make_preparer(get_assignment: Callable[[], Assignment]) -> Callable[[DataBundle], Optional[DataBundle]]:
    """A function to give to ``add_data_preparer``, reading the assignment when called (it can change)"""
    def preparer(bundle: DataBundle) -> DataBundle:
        return annotate_bundle(bundle, get_assignment())
    return preparer


def embed_excerpt(h5saver, source, assignment: Assignment) -> bool:
    """Save in the file the part of the ontology describing the assigned terms, so that the file can be read without
    the ontology: group ``Ontology`` of the root, with the string array ``excerpt`` and the attributes ``format``,
    ``iri`` and ``version`` (the last two when the source knows them).
    Returns False if there is nothing to save or the file cannot be written."""
    iris = sorted({iri for iri in assignment.values.values() if iri})
    if source is None or not iris or h5saver is None:
        return False
    try:
        text, info = source.excerpt(iris)
        if not text:
            return False
        group = h5saver.get_set_group('/', EMBEDDED_GROUP)
        h5saver.add_string_array(group, EMBEDDED_TEXT).append(text)
        for name, value in {'format': 'turtle', **info}.items():
            h5saver.set_attr(group, name, value)
        return True
    except Exception as e:  # an excerpt that cannot be written must never stop the saving of the data
        logger.warning(f'Could not save the ontology excerpt in the file: {e}')
        return False


def make_embedder(get_source: Callable[[], object], get_assignment: Callable[[], Assignment],
                  get_h5saver: Callable[[], object]) -> Callable[[DataBundle], Optional[DataBundle]]:
    """A function to give to ``add_data_preparer``: with the first bundle of an acquisition, saves the excerpt of the
    ontology (see :func:`embed_excerpt`). The file is then open and no other bundle is being saved."""
    def embedder(bundle: DataBundle) -> DataBundle:
        if not bundle.save_index:
            embed_excerpt(get_h5saver(), get_source(), get_assignment())
        return bundle
    return embedder
