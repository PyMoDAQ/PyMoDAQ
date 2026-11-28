import numpy as np

from pymodaq_data.data import DataToExport, DataRaw
from pymodaq_data.h5modules.data_saving import DataBundle

from pymodaq_ontology.annotation import annotate_bundle, make_annotator
from pymodaq_ontology.assignment import Assignment


def bundle(save_index=0):
    dwa = DataRaw('Spec', source='raw', data=[np.array([1.]), np.array([2.])], labels=['a', 'b'])
    dwa.origin = 'Det'
    return DataBundle(dte=DataToExport('d', data=[dwa]), save_index=save_index)


def test_same_term_gives_one_iri():
    a = Assignment({'Det/Spec/a': 'x', 'Det/Spec/b': 'x'})
    assert annotate_bundle(bundle(), a).dte.data[0].semantic_iri == 'x'


def test_different_terms_give_a_list():
    a = Assignment({'Det/Spec/a': 'x'})
    assert annotate_bundle(bundle(), a).dte.data[0].semantic_iri == ['x', '']


def test_nothing_assigned_and_later_bundles_untouched():
    assert 'semantic_iri' not in annotate_bundle(bundle(), Assignment()).dte.data[0].extra_attributes
    b = annotate_bundle(bundle(1), Assignment({'Det/Spec/a': 'x'}))
    assert 'semantic_iri' not in b.dte.data[0].extra_attributes


def test_annotator_reads_current_assignment():
    a = Assignment()
    annotator = make_annotator(lambda: a)
    a.set('Det/Spec/a', 'x')
    assert annotator(bundle()).dte.data[0].semantic_iri == ['x', '']
