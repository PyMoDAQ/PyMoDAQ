import pytest

from pymodaq_ontology.assignment import Assignment, load_entry, save_entry
from pymodaq_ontology.source_factory import OntologySource, SourceFactory
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, OntologyTerm


class TestTerm:
    def test_term_without_roles_fits_any_channel(self):
        term = OntologyTerm('iri', 'label')
        assert term.fits(DETECTOR) and term.fits(ACTUATOR)

    def test_term_with_roles(self):
        term = OntologyTerm('iri', 'label', roles=(DETECTOR,))
        assert term.fits(DETECTOR)
        assert not term.fits(ACTUATOR)


class TestSources:
    def test_terms_file_source(self, source):
        terms = {term.label: term for term in source.terms()}
        assert set(terms) == {'Photodiode signal A', 'Applied magnetic field', 'Sample temperature'}
        assert terms['Photodiode signal A'].roles == (DETECTOR,)
        assert terms['Sample temperature'].roles == ()  # unknown: fits everything
        assert terms['Sample temperature'].category == 'Environment'

    def test_identifier_round_trip(self, source):
        again = SourceFactory.from_identifier(source.identifier)
        assert again.location == source.location
        assert again.source_type == 'terms'

    def test_unknown_type(self):
        with pytest.raises(ValueError):
            SourceFactory.create('no_such_type', 'somewhere')

    def test_registering_a_source_type(self):
        @SourceFactory.register
        class FixedSource(OntologySource):
            source_type = 'fixed_for_test'

            def terms(self):
                return [OntologyTerm('a', 'A')]

        try:
            assert 'fixed_for_test' in SourceFactory.names()
            assert [t.iri for t in SourceFactory.create('fixed_for_test', '').terms()] == ['a']
        finally:
            SourceFactory._types.pop('fixed_for_test')

    def test_source_type_is_required(self):
        class NoType(OntologySource):
            def terms(self):
                return []

        with pytest.raises(NotImplementedError):
            SourceFactory.register(NoType)


class TestAssignment:
    def test_set_and_clear(self):
        assignment = Assignment()
        assignment.set('Magnet', 'iri')
        assert assignment.get('Magnet') == 'iri'
        assignment.set('Magnet', '')
        assert assignment.get('Magnet') == ''
        assert 'Magnet' not in assignment.values

    def test_entry_round_trip(self, tmp_path, source):
        path = tmp_path / 'default.ontology'
        assignment = Assignment({'Detector/Data0D/CH00': 'http://example.org/moke#PhotodiodeSignalA',
                                 'Magnet': 'http://example.org/moke#MagneticField'})
        save_entry(path, assignment, source)

        loaded, loaded_source = load_entry(path)
        assert loaded.values == assignment.values
        assert loaded_source.identifier == source.identifier

    def test_entry_without_source_or_with_unknown_type(self, tmp_path):
        path = tmp_path / 'default.ontology'
        save_entry(path, Assignment({'a': 'b'}))
        assert load_entry(path)[1] is None

        path.write_text('[source]\ntype = "gone"\nlocation = "x"\n[assignments]\na = "b"\n')
        loaded, loaded_source = load_entry(path)
        assert loaded.values == {'a': 'b'} and loaded_source is None
