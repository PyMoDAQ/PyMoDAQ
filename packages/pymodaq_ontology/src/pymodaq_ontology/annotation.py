"""Write the assigned terms in the data to be saved, as the ``semantic_iri`` extra attribute of the arrays"""
from typing import Callable, Optional

from pymodaq_data.h5modules.data_saving import DataBundle

from pymodaq_ontology.assignment import Assignment
from pymodaq_ontology.channels import Channel
from pymodaq_ontology.terms import ACTUATOR, DETECTOR

ATTRIBUTE = 'semantic_iri'


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
