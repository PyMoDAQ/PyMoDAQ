import pytest
from qtpy import QtCore
from qtpy.QtTest import QTest

from pymodaq_ontology.term_picker import TermPicker, IRI_ROLE
from pymodaq_ontology.terms import ACTUATOR, DETECTOR


@pytest.fixture
def terms(source):
    return source.terms()


def listed(picker):
    return [leaf.text(0) for _, leaf in picker._leaves() if not leaf.isHidden()]


def test_only_the_terms_fitting_the_kind_then_all(qtbot, terms):
    picker = TermPicker(terms, kind=ACTUATOR)
    qtbot.addWidget(picker)
    assert listed(picker) == ['Applied magnetic field', 'Sample temperature']  # unknown roles fit everything

    picker.show_all.setChecked(True)
    assert len(listed(picker)) == 3


def test_typing_filters_and_selects_the_first_term_then_enter_validates(qtbot, terms):
    picker = TermPicker(terms, kind=DETECTOR)
    qtbot.addWidget(picker)
    picker.show_all.setChecked(True)

    picker.search.setText('magnetic')
    assert listed(picker) == ['Applied magnetic field']
    QTest.keyClick(picker, QtCore.Qt.Key.Key_Return)

    assert picker.selected_iri == 'http://example.org/moke#MagneticField'
    assert picker.result() == picker.DialogCode.Accepted


def test_current_term_is_preselected(qtbot, terms):
    picker = TermPicker(terms, current_iri='http://example.org/moke#SampleTemperature')
    qtbot.addWidget(picker)
    assert picker.tree.currentItem().data(0, IRI_ROLE) == 'http://example.org/moke#SampleTemperature'


def test_no_selection_when_nothing_is_picked(qtbot, terms):
    picker = TermPicker(terms)
    qtbot.addWidget(picker)
    picker.tree.setCurrentItem(None)
    picker._accept()
    assert picker.selected_iri == ''
