from pathlib import Path
from unittest import mock

import numpy as np
import pytest

from pymodaq_data.data import Axis, DataRaw, DataToExport
from pymodaq_data.h5modules.browsing import H5BrowserUtil
from pymodaq_data.h5modules.data_saving import DataToExportSaver
from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq_data.h5modules import representations as rep

NS = 'https://w3id.org/pymodaq/spectro#'


def make_file(path: Path, items, group: str = 'Spectrometer', ontology: str = ''):
    """items: (name, units, concept or None, quantity kind or None, unit iri or None)"""
    dte = DataToExport('test')
    for name, units, concept, qk, unit_iri in items:
        data = DataRaw(name, data=[np.random.rand(10)], units=units, labels=[name],
                       axes=[Axis('x', data=np.linspace(0, 1, 10), index=0)])
        if concept:
            data.add_extra_attribute(semantic_iri=NS + concept, quantity_kind=qk, unit_iri=unit_iri)
        dte.append(data)
    h5 = H5SaverLowLevel()
    h5.init_file(file_name=path, new_file=True)
    DataToExportSaver(h5).add_data(h5.get_set_group(h5.raw_group, group), dte)
    if ontology:  # excerpt of the ontology embedded in the file
        h5.set_attr(h5.get_set_group('/', rep.EMBEDDED_GROUP), 'excerpt', ontology)
    h5.close_file()
    return path


def infos_of(path: Path):
    h5 = H5BrowserUtil(backend='h5py')
    h5.init_file(file_name=path, new_file=False, mode='r')
    try:
        return rep.data_infos(h5.root(), path.stem), h5
    finally:
        h5.close_file()


@pytest.fixture
def lab_a(tmp_path):
    return make_file(tmp_path / 'lab_a.h5', [
        ('background', 'counts', 'DarkSpectrum', 'qk:Count', 'unit:NUM'),
        ('reference', 'counts', 'ReferenceSpectrum', 'qk:Count', 'unit:NUM'),
        ('signal', 'counts', 'SampleSpectrum', 'qk:Count', 'unit:NUM'),
        ('other', 'V', None, None, None)])


@pytest.fixture
def lab_b(tmp_path):
    return make_file(tmp_path / 'lab_b.h5', [
        ('Trans', '%', 'TransmittanceSpectrum', 'qk:Transmittance', 'unit:PERCENT'),
        ('dark', 'counts', 'DarkSpectrum', 'qk:Count', 'unit:NUM')])


def test_helpers():
    assert rep.local_name(NS + 'DarkSpectrum') == 'DarkSpectrum'
    assert rep.local_name('unit:NUM') == 'NUM'
    assert rep.SemanticsBase().label(NS + 'DarkSpectrum') == 'Dark spectrum'


def test_data_infos(lab_a):
    infos, _ = infos_of(lab_a)
    data = [i for i in infos if i.kind == 'data']
    assert sorted(i.label for i in data) == ['background', 'other', 'reference', 'signal']
    assert all(i.path.startswith('/RawData/Spectrometer/') for i in infos)
    assert all(i.attrs['data_type'] == 'data' for i in data)
    axes = [i for i in infos if i.kind == 'axis']          # the axes are listed too, with their context
    assert len(axes) == 4 and {i.label for i in axes} == {'x'}
    assert sorted(i.owner for i in axes) == ['background', 'other', 'reference', 'signal']
    assert {i.role for i in axes} == {'signal'}


def test_concept_mode(lab_a):
    infos, _ = infos_of(lab_a)
    tree = rep.build_mode('concept', infos)
    assert [c.label for c in tree.children] == ['Dark spectrum', 'Reference spectrum',
                                                'Sample spectrum', rep.UNANNOTATED]
    dark = tree.find('Dark spectrum')
    assert dark.path is None and len(dark.children) == 1
    assert dark.children[0].label == 'background'
    node_paths = {i.path for i in infos}
    # every leaf points to an existing data node, grouping items point to nothing
    assert {n.path for n in tree.walk() if n.path} == {i.path for i in infos if i.kind == 'data'}  # no axes here


def test_quantity_mode(lab_a):
    infos, _ = infos_of(lab_a)
    tree = rep.build_mode('quantity', infos)
    count = tree.find('Count')
    assert [u.label for u in count.children] == ['counts']  # the `units` attribute, the IRI is in the tooltip
    assert count.children[0].tooltip == 'unit:NUM'
    assert sorted(l.label for l in count.children[0].children) == ['background', 'reference', 'signal']
    # not annotated data still grouped by the plain `units` attribute
    assert tree.find(rep.UNANNOTATED).find('V').children[0].label == 'other'


def test_two_files_share_concepts(lab_a, lab_b):
    infos = infos_of(lab_a)[0] + infos_of(lab_b)[0]
    tree = rep.build_mode('concept', infos)
    dark = tree.find('Dark spectrum')
    assert sorted(c.label for c in dark.children) == ['background [lab_a]', 'dark [lab_b]']
    assert tree.find('Transmittance spectrum') is not None


def test_register_mode(lab_a):
    infos, _ = infos_of(lab_a)

    @rep.register_mode('flat', 'Flat')
    def flat(infos, semantics):
        return rep.RepItem('All', children=[rep.RepItem(x.label, x.path) for x in infos if x.kind == 'data'])

    try:
        assert 'flat' in rep.mode_names() and rep.mode_title('flat') == 'Flat'
        assert len(rep.build_mode('flat', infos).children) == 4
    finally:
        del rep.RepresentationModeFactory.builders['flat']


class Onto(rep.SemanticsBase):
    """Knows the 'Spectrum' concept and that every ...Spectrum is a Spectrum"""
    def knows(self, iri):
        return iri.endswith('Spectrum')

    def label(self, iri):
        return 'Spectrum' if iri == NS + 'Spectrum' else super().label(iri)

    def parent(self, iri):
        return NS + 'Spectrum' if iri != NS + 'Spectrum' else None


def test_semantics_provider_gives_hierarchy_and_labels(lab_a):
    infos, _ = infos_of(lab_a)
    tree = rep.build_mode('concept', infos, Onto())
    spectrum = tree.find('Spectrum')
    assert [c.label for c in spectrum.children] == ['Dark spectrum', 'Reference spectrum', 'Sample spectrum']
    assert spectrum.find('Dark spectrum').children[0].label == 'background'
    assert tree.find(rep.UNANNOTATED) is not None
    # no global state: without the argument the tree is flat again
    assert rep.build_mode('concept', infos).find('Dark spectrum') is not None


def test_registered_provider_by_name(lab_a):
    rep.SemanticsFactory.register('test_onto')(Onto)
    try:
        assert isinstance(rep.get_semantics('test_onto'), Onto)
        assert rep.build_tree(lab_a, 'concept', rep.get_semantics('test_onto')).find('Spectrum') is not None
    finally:
        del rep.SemanticsFactory.providers['test_onto']


def test_composite_semantics(lab_a):
    class Volts(rep.SemanticsBase):
        def knows(self, iri):
            return iri == 'qk:Count'

        def label(self, iri):
            return 'Detector counts'

    composite = rep.CompositeSemantics([Volts(), Onto()])
    assert composite.label('qk:Count') == 'Detector counts'          # first provider
    assert composite.label(NS + 'Spectrum') == 'Spectrum'            # second provider
    assert composite.label(NS + 'SomethingElse') == 'Something else'  # nobody knows: default
    assert composite.parent(NS + 'DarkSpectrum') == NS + 'Spectrum'
    tree = rep.build_tree(lab_a, 'quantity', composite)
    assert tree.find('Detector counts') is not None


def test_build_tree_and_notebook_rendering(lab_a, lab_b):
    tree = rep.build_tree([lab_a, lab_b], 'concept')
    assert 'Dark spectrum' in str(tree)
    assert 'background [lab_a]  -> /RawData/Spectrometer/Data1D/CH00/Data00' in str(tree)
    html_repr = tree._repr_html_()
    assert '<details' in html_repr and '<code>/RawData' in html_repr
    assert rep.RepItem('<b>', None)._repr_html_().count('<b>') == 0  # labels are escaped
    assert rep.build_tree(lab_a, 'quantity').find('Count') is not None


def test_dataloader_describe(lab_a):
    from pymodaq_data.h5modules.data_saving import DataLoader
    with DataLoader(lab_a) as loader:
        tree = loader.describe('concept')
    assert tree.find('Dark spectrum').children[0].label == 'background'  # one file: no file name added
    with DataLoader(lab_a) as loader:
        assert 'Data00 · background [counts]' in str(loader.describe('hdf5'))


def test_unknown_names_raise(lab_a):
    with pytest.raises(ValueError):
        rep.build_mode('nope', [])
    with pytest.raises(ValueError):
        rep.get_semantics('nope')


def test_replacing_a_registered_name_warns(lab_a):
    with mock.patch.object(rep.logger, 'warning') as warning:
        rep.register_mode('concept', 'By concept')(rep.concept_mode)  # same name again
    assert warning.called and 'already registered' in warning.call_args[0][0]


TTL = f"""
@prefix : <{NS}> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
:Spectrum a rdfs:Class ; rdfs:label "Spectrum"@en .
:DarkSpectrum rdfs:subClassOf :Spectrum ; rdfs:label "Dark (shutter closed)"@en, "Sombre"@fr .
:SampleSpectrum rdfs:subClassOf :Spectrum ; skos:prefLabel "Sample"@en ; rdfs:label "ignored"@en .
:ReferenceSpectrum rdfs:subClassOf :Spectrum .
"""


@pytest.fixture
def ttl(tmp_path):
    pytest.importorskip('rdflib')
    path = tmp_path / 'onto.ttl'
    path.write_text(TTL)
    return path


def test_labels_and_parents(ttl):
    RdfSemantics = pytest.importorskip('pymodaq_data.h5modules.semantics_rdf').RdfSemantics
    sem = RdfSemantics(ttl)
    assert sem.label(NS + 'DarkSpectrum') == 'Dark (shutter closed)'   # english, not french
    assert sem.label(NS + 'SampleSpectrum') == 'Sample'                # skos:prefLabel first
    assert sem.label(NS + 'ReferenceSpectrum') == 'Reference spectrum'  # no label: default
    assert sem.parent(NS + 'DarkSpectrum') == NS + 'Spectrum'
    assert sem.parent(NS + 'Spectrum') is None
    assert sem.knows(NS + 'Spectrum') and not sem.knows(NS + 'Other')


def test_registered_as_rdf_and_used_by_modes(lab_a, ttl):
    pytest.importorskip('rdflib')
    sem = rep.get_semantics('rdf', sources=[str(ttl)])
    tree = rep.build_tree(lab_a, 'concept', sem)
    spectrum = tree.find('Spectrum')
    assert [c.label for c in spectrum.children] == ['Dark (shutter closed)', 'Reference spectrum', 'Sample']
    assert spectrum.find('Sample').children[0].label == 'signal'


def test_explicit_node_name(lab_a):
    h5 = H5BrowserUtil(backend='h5py')
    h5.init_file(file_name=lab_a, new_file=False, mode='r')
    try:
        base = '/RawData/Spectrometer/Data1D/CH00'
        assert rep.explicit_node_name('CH00', h5.get_node(base)) == 'CH00 · background'
        assert rep.explicit_node_name('Data00', h5.get_node(base + '/Data00')) == 'Data00 · background [counts]'
        assert rep.explicit_node_name('Axis00', h5.get_node(base + '/Axis00')) == 'Axis00 · x'
        assert rep.explicit_node_name('Data1D', h5.get_node('/RawData/Spectrometer/Data1D')) == 'Data1D'
    finally:
        h5.close_file()


def test_quantity_mode_lists_axes_apart(lab_a, lab_b, tmp_path):
    tree = rep.build_tree([lab_a, lab_b], 'quantity')
    assert [c.label for c in tree.children][-1] == 'Axes'      # data branches first, axes last
    axes = tree.find('Axes')
    # the test files have an axis without quantity kind: they are not annotated
    unannotated = axes.find(rep.UNANNOTATED)
    leaf = unannotated.children[0].children[0]
    assert leaf.label.startswith('Axis00 · x') and 'signal axis' in leaf.label and '[lab_a]' in leaf.label
    assert leaf.path.endswith('/Axis00')
    # no axis among the data branches
    assert all(n.path is None or n.path.endswith('Data00') for c in tree.children[:-1] for n in c.walk())


def test_axis_role_signal_or_navigation(tmp_path):
    from pymodaq_data.data import DataRaw
    scan = DataRaw('scan', data=[np.random.rand(3, 10)], nav_indexes=(0,), labels=['scan'],
                   axes=[Axis('field', units='T', data=np.arange(3.), index=0),
                         Axis('wl', units='nm', data=np.arange(10.), index=1)])
    scan.axes[0].add_extra_attribute(quantity_kind='qk:MagneticFluxDensity', unit_iri='unit:T')
    scan.axes[1].add_extra_attribute(quantity_kind='qk:Wavelength', unit_iri='unit:NanoM')
    h5 = H5SaverLowLevel()
    path = tmp_path / 'scan.h5'
    h5.init_file(file_name=path, new_file=True)
    DataToExportSaver(h5).add_data(h5.get_set_group(h5.raw_group, 'Det'), DataToExport('t', data=[scan]))
    h5.close_file()
    infos, _ = infos_of(path)
    roles = {i.label: i.role for i in infos if i.kind == 'axis'}
    assert roles == {'field': 'navigation', 'wl': 'signal'}
    axes = rep.build_mode('quantity', infos).find('Axes')
    assert 'navigation axis' in axes.find('Magnetic flux density').children[0].children[0].label
    assert 'signal axis' in axes.find('Wavelength').children[0].children[0].label


def test_build_tree_standard_hierarchy_matches_the_browser_names(lab_a, lab_b):
    tree = rep.build_tree(lab_a, 'hdf5')
    text = str(tree)
    assert 'CH00 · background' in text and 'Data00 · background [counts]' in text and 'Axis00 · x' in text
    assert tree.label == 'lab_a'
    leaf = next(n for n in tree.walk() if n.label.startswith('Data00 · background'))
    assert leaf.path == '/RawData/Spectrometer/Data1D/CH00/Data00'
    group = next(n for n in tree.walk() if n.label == 'Spectrometer')
    assert group.path == '/RawData/Spectrometer'  # groups keep their path too
    both = rep.build_tree([lab_a, lab_b], 'hdf5')
    assert [c.label for c in both.children] == ['lab_a', 'lab_b']


def test_main_groups_shown_only_when_data_come_from_several_groups(lab_a, tmp_path):
    assert rep.main_group('/RawData/scan_000/Data1D/CH00/Data00') == 'scan_000'
    assert rep.main_group('/RawData/Det/Data0D/CH00/Axis00') == 'Det'
    assert ' · Spectrometer' not in rep.build_tree(lab_a, 'concept').to_text()  # a single group: no noise

    two = make_file(tmp_path / 'two.h5', [('noir', 'counts', 'DarkSpectrum', 'qk:Count', 'unit:NUM')],
                    group='scan_001')
    text = rep.build_tree([lab_a, two], 'concept').to_text()
    assert 'noir · scan_001 [two]' in text and 'background · Spectrometer [lab_a]' in text
    assert 'scan_001' in rep.build_tree([lab_a, two], 'quantity').to_text()


EQUIVALENT_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://w3id.org/pymodaq/spectro#DarkSpectrum> rdfs:label "Dark"@en ;
    owl:equivalentClass <http://other.org/vocab#DarkCurrent> .
<http://other.org/vocab#DarkCurrent> rdfs:label "Dark current"@en .
"""


def test_canonical_groups_equivalent_terms(tmp_path):
    pytest.importorskip('rdflib')
    sem = rep.get_semantics('rdf', text=EQUIVALENT_TTL)
    a, b = NS + 'DarkSpectrum', 'http://other.org/vocab#DarkCurrent'
    assert sem.canonical(a) == sem.canonical(b)
    assert sem.canonical(NS + 'Unknown') == NS + 'Unknown'
    assert rep.SemanticsBase().canonical(a) == a
    path = make_file(tmp_path / 'f.h5', [('d1', 'counts', 'DarkSpectrum', None, None)])
    other = make_file(tmp_path / 'g.h5', [('d2', 'counts', 'X', None, None)])
    infos, _ = infos_of(path)
    infos2, _ = infos_of(other)
    next(i for i in infos2 if i.kind == 'data').attrs['semantic_iri'] = b  # annotated with the other vocabulary
    tree = rep.build_mode('concept', [i for i in infos + infos2 if i.kind == 'data'], sem)
    concepts = [c for c in tree.children if c.label != rep.UNANNOTATED]
    assert len(concepts) == 1 and len(concepts[0].children) == 2


def test_embedded_ontology_is_read_from_the_file(tmp_path):
    pytest.importorskip('rdflib')
    items = [('d1', 'counts', 'DarkSpectrum', None, None)]
    plain = make_file(tmp_path / 'plain.h5', items)
    with_ontology = make_file(tmp_path / 'with.h5', items, ontology=EQUIVALENT_TTL)
    for path, expected in ((plain, False), (with_ontology, True)):
        h5 = H5BrowserUtil(backend='h5py')
        h5.init_file(file_name=path, new_file=False, mode='r')
        try:
            sem = rep.embedded_semantics(h5.root())
            assert (sem is not None) == expected
            if sem:
                assert sem.label(NS + 'DarkSpectrum') == 'Dark'
                assert sem.canonical('http://other.org/vocab#DarkCurrent') == sem.canonical(NS + 'DarkSpectrum')
        finally:
            h5.close_file()
