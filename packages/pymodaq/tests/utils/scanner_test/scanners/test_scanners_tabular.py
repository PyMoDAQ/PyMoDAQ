# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
import numpy as np
import pytest

from .conftest import assert_steps_consistent


def as_table(array) -> list:
    """The table models store their cells as strings"""
    return [[str(elt) for elt in row] for row in np.atleast_2d(array)]


class TestScannerTabular:
    @pytest.mark.parametrize('n_act', [1, 2, 3])
    @pytest.mark.parametrize('n_points', [1, 2, 7, 50])
    def test_evaluate_steps_linear(self, make_scanner, n_act, n_points):
        scanner = make_scanner('Tabular', 'Linear', n_act=n_act)
        scanner.update_model(as_table(np.random.rand(n_points, n_act)))
        assert_steps_consistent(scanner)

    def test_evaluate_steps_default(self, make_scanner):
        scanner = make_scanner('Tabular', 'Linear', n_act=2)
        assert_steps_consistent(scanner)

    @pytest.mark.parametrize('step', [0.1, 0.3, 0.5, 1.])
    @pytest.mark.parametrize('points', [
        [[0., 0.], [1., 1.]],
        [[0., 0.], [1., 0.], [1., 1.]],
        [[0., 0.], [1., 0.], [1., 1.], [0., 1.], [0., 0.]],
    ])
    @pytest.mark.xfail(strict=True, reason='TableModelTabular casts cells to str and set_scan builds Points from them '
                                          '(numpy cannot subtract strings): set_scan fails with 2 points or more')
    def test_evaluate_steps_subsegmented(self, make_scanner, points, step):
        scanner = make_scanner('Tabular', 'SubSegmented', n_act=2)
        scanner.settings['tabular_step'] = step
        scanner.update_model_points(np.array(points))
        assert_steps_consistent(scanner)
