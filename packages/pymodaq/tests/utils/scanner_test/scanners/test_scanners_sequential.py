# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
import pytest

from .conftest import assert_steps_consistent, known_bug

TRUNCATION = (
    'evaluate_steps computes int(abs(delta / step) + 1) (float noise, no ceil) while set_scan uses the scan loop (ceil-like, stop inclusive)')

# one (start, stop, step) per actuator
conditions = [
    [(0., 1., 0.1)],
    [(0., 1., 0.3)],
    [(0., 1., 0.25), (0., 1., 0.5)],
    known_bug([(0., 1., 0.3), (0., 1., 0.25)], reason=TRUNCATION),
    [(0., 1., 1 / 3), (0., 1., 1 / 7)],
    [(0., 2., 1.), (0., 3., 1.), (0., 2., 1.)],
    known_bug([(0., 1., 0.7), (-1., 1., 0.4), (0., 0.5, 0.2)], reason=TRUNCATION),
    [(1., 0., -0.1), (0., 1., 0.1)],
    known_bug([(1., -1., -0.3), (3., 0., -0.7)], reason=TRUNCATION),
    known_bug([(0., 1., 2.), (0., 1., 2.)], reason=TRUNCATION),  # steps larger than the ranges
]


class TestScannerSequential:
    @pytest.mark.parametrize('cond', conditions)
    def test_evaluate_steps(self, make_scanner, cond):
        scanner = make_scanner('Sequential', 'Linear', n_act=len(cond))
        init_data = [[f'act_{ind}', f'{start}', f'{stop}', f'{step}']
                     for ind, (start, stop, step) in enumerate(cond)]
        scanner.update_model(init_data)
        assert_steps_consistent(scanner)
