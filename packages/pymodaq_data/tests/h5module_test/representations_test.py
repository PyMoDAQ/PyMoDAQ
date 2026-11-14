from pathlib import Path

import numpy as np
import pytest

from pymodaq_data.data import Axis, DataRaw, DataToExport
from pymodaq_data.h5modules.browsing import H5BrowserUtil
from pymodaq_data.h5modules.data_saving import DataToExportSaver
from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq_data.h5modules import representations as rep

NS = 'https://w3id.org/pymodaq/spectro#'


def make_file(path: Path, items):
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
    DataToExportSaver(h5).add_data(h5.get_set_group(h5.raw_group, 'Spectrometer'), dte)
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
    assert rep.iri_label(NS + 'DarkSpectrum') == 'Dark spectrum'


def test_data_infos(lab_a):
    infos, _ = infos_of(lab_a)
    assert sorted(i.label for i in infos) == ['background', 'other', 'reference', 'signal']
    assert all(i.path.startswith('/RawData/Spectrometer/') for i in infos)
    assert all(i.attrs['data_type'] == 'data' for i in infos)  # axes are not listed


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
    assert {n.path for n in tree.walk() if n.path} == node_paths


def test_quantity_mode(lab_a):
    infos, _ = infos_of(lab_a)
    tree = rep.build_mode('quantity', infos)
    count = tree.find('Count')
    assert [u.label for u in count.children] == ['NUM']
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
    def flat(infos):
        return rep.RepItem('All', children=[rep.RepItem(x.label, x.path) for x in infos])

    try:
        assert 'flat' in rep.mode_names() and rep.mode_title('flat') == 'Flat'
        assert len(rep.build_mode('flat', infos).children) == 4
    finally:
        del rep.RepresentationModeFactory._builders['RepresentationModeFactory']['flat']


def test_semantics_provider_gives_hierarchy_and_labels(lab_a):
    infos, _ = infos_of(lab_a)

    @rep.SemanticsFactory.register('test_onto')
    class Onto(rep.SemanticsBase):
        def label(self, iri):
            return 'Spectrum' if iri == NS + 'Spectrum' else super().label(iri)

        def parent(self, iri):
            return NS + 'Spectrum' if iri.endswith('Spectrum') and iri != NS + 'Spectrum' else None

    try:
        rep.set_semantics('test_onto')
        tree = rep.build_mode('concept', infos)
        spectrum = tree.find('Spectrum')
        assert [c.label for c in spectrum.children] == ['Dark spectrum', 'Reference spectrum', 'Sample spectrum']
        assert spectrum.find('Dark spectrum').children[0].label == 'background'
        assert tree.find(rep.UNANNOTATED) is not None
    finally:
        rep.set_semantics('default')
        del rep.SemanticsFactory._builders['SemanticsFactory']['test_onto']
    assert rep.build_mode('concept', infos).find('Dark spectrum') is not None  # flat again


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
