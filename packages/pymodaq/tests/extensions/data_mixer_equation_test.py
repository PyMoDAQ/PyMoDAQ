"""The formulas of the data mixer are typed by users or come from their saved configuration: computing one
must never be able to run anything else than arithmetic and numpy functions on the data.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from pymodaq_data.data import DataRaw, DataToExport
from pymodaq_gui.parameter import Parameter
from pymodaq.extensions.data_mixer.models.equation_model import DataMixerModelEquation


@pytest.fixture
def model():
    settings = Parameter.create(name='settings', type='group', children=[
        {'name': 'models', 'type': 'group', 'children': [{'name': 'model_params', 'type': 'group'}]}])
    return DataMixerModelEquation(SimpleNamespace(modules_manager=None, settings=settings))


@pytest.fixture
def dte():
    return DataToExport('raw', data=[
        DataRaw('a', origin='det', data=[np.array([1., 2., 3.])]),
        DataRaw('b', origin='det', data=[np.array([10., 20., 30.])]),
    ])


def test_methods_of_the_data_can_be_used(model, dte):
    result = compute(model, dte, '{det/b}.mean() - {det/a}.sum()')

    assert np.allclose(result[0], [20. - 6.])


def test_methods_of_the_data_change_the_result_as_expected(model, dte):
    result = compute(model, dte, 'np.sqrt({det/a}.mean() ** 2) + {det/b}.mean() * 0')

    assert np.allclose(result[0], [2.])


def compute(model, dte, formula):
    return model.compute_formula(formula, dte, name='result')


@pytest.mark.parametrize('formula, expected', [
    ('{det/a} + {det/b}', [11., 22., 33.]),
    ('{det/b} - {det/a}', [9., 18., 27.]),
    ('2 * {det/a}', [2., 4., 6.]),
    ('{det/a} * {det/b} / 10', [1., 4., 9.]),
    ('-{det/a}', [-1., -2., -3.]),
    ('{det/a} ** 2', [1., 4., 9.]),
    ('np.abs(-{det/a})', [1., 2., 3.]),
    ('np.sqrt({det/a} ** 2) + np.sin(0)', [1., 2., 3.]),
    ('{det/a} * np.pi / np.pi', [1., 2., 3.]),
    ('np.add({det/a}, {det/b})', [11., 22., 33.]),
    ('np.abs({det/a} - 2.5 * 1e0)', [1.5, 0.5, 0.5]),
    ('-{det/a}.abs()', [-1., -2., -3.]),
    ('{det/a}.deepcopy() + {det/b}.abs()', [11., 22., 33.]),
])
def test_formulas_are_computed(model, dte, formula, expected):
    result = compute(model, dte, formula)

    assert result.name == 'result'
    assert np.allclose(result[0], expected)


@pytest.mark.parametrize('formula', [
    "__import__('sys').version",
    "{det/a} + __import__('sys').maxsize",
    "np.sys.version",
    "np.os.getcwd()",
    "{det/a}.__class__.__mro__",
    "().__class__",
    "[x for x in (1, 2)]",
    "(lambda: 1)()",
    "open('a_file_that_should_not_be_opened')",
    "np.load('a_file_that_should_not_be_opened')",
    "np.savetxt('a_file_that_should_not_be_created', [1])",
    "dte.__class__",
    "dte.data",
    "{det/a}.__class__",
    "{det/a}._data",
    "{det/a}.data",
    "{det/a}.mean().__class__",
    "{det/a}.mean().data[0].tofile('a_file_that_should_not_be_created')",
    "np.array([1, 2]).tofile('a_file_that_should_not_be_created')",
    "np.array([1, 2]).dump('a_file_that_should_not_be_created')",
    "np.array([1, 2]).tolist()",
    "(1).bit_length()",
    "np.__dict__",
    "{det/a} if True else 1",
])
def test_anything_else_than_arithmetic_and_numpy_is_refused(model, dte, formula, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # so that a formula writing a file cannot dirty the repository

    with pytest.raises(Exception) as exc_info:
        compute(model, dte, formula)

    assert type(exc_info.value).__name__ == 'UnsafeFormulaError'
    assert list(tmp_path.iterdir()) == []
