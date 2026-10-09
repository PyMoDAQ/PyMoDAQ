# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
import numpy as np
import pytest

from .conftest import assert_steps_consistent

# one (start, stop, step) per actuator
conditions = [
    [(0., 1., 0.1)],
    [(0., 1., 0.3)],
    [(0., 1., 0.25), (0., 1., 0.5)],
    [(0., 1., 0.3), (0., 1., 0.25)],
    [(0., 1., 1 / 3), (0., 1., 1 / 7)],
    [(0., 2., 1.), (0., 3., 1.), (0., 2., 1.)],
    [(0., 1., 0.7), (-1., 1., 0.4), (0., 0.5, 0.2)],
    [(1., 0., -0.1), (0., 1., 0.1)],
    [(1., -1., -0.3), (3., 0., -0.7)],
    [(0., 1., 2.), (0., 1., 2.)],  # steps larger than the ranges
    [(0., 0.7, 0.1), (0., 0.7, 0.1)],
    [(0., 1., -0.1), (0., 1., 0.1)],  # invalid axis, reduced to its start value
    [(0., 1., 0.), (0., 1., 0.1)],
]


class TestScannerSequential:
    @pytest.mark.parametrize('cond', conditions)
    def test_evaluate_steps(self, make_scanner, cond):
        scanner = make_scanner('Sequential', 'Linear', n_act=len(cond))
        init_data = [[f'act_{ind}', f'{start}', f'{stop}', f'{step}']
                     for ind, (start, stop, step) in enumerate(cond)]
        scanner.update_model(init_data)
        assert_steps_consistent(scanner)

    def test_positions_order(self, make_scanner):
        """The first actuator is the slowest one, the last one the fastest"""
        scanner = make_scanner('Sequential', 'Linear', n_act=2)
        scanner.update_model([['act_0', '0', '1', '1'], ['act_1', '0', '2', '1']])
        assert_steps_consistent(scanner)
        assert np.array_equal(scanner.positions, [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]])
