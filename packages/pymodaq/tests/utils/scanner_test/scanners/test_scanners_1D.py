# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
import pytest

from .conftest import assert_steps_consistent, known_bug

TRUNCATION = (
    'evaluate_steps computes int(abs(delta / step) + 1) (float noise, no ceil) while set_scan uses linspace_step (ceil + tolerance)')

linear_conditions = [
    (0., 1., 0.1),
    (0., 1., 0.3),
    (0., 1., 0.25),
    (0., 1., 0.7),
    (0., 1., 1 / 3),
    (0., 10., 1.),
    (0., 1., 0.01),
    known_bug(0., 0.7, 0.1, reason=TRUNCATION),
    (-1., 1., 0.2),
    (-5.3, 7.1, 0.37),
    (1., 0., -0.1),
    (1., -1., -0.3),
    (5., 0., -1.),
    (0., 1e-3, 1e-4),
    (0., 1e3, 7.),
    (0., 1., 2.),  # step larger than the range
]


class TestScanner1D:
    @pytest.mark.parametrize('subtype', ['Linear', 'Random'])
    @pytest.mark.parametrize('start, stop, step', linear_conditions)
    def test_evaluate_steps_linear(self, make_scanner, subtype, start, stop, step):
        scanner = make_scanner('Scan1D', subtype)
        scanner.settings['start'] = start
        scanner.settings['stop'] = stop
        scanner.settings['step'] = step
        assert_steps_consistent(scanner)

    @pytest.mark.parametrize('parsed_string', [
        '0:0.1:1',
        '0:0.2:1',
        '0:0.3:1',
        '0',
        '0:0.2:1,5',
        '0:0.2:1,5:1:7',
        '0:0.2:1\n5:1:7\n10',
        '1:-0.1:0',
        '0,1,2,3',
    ])
    def test_evaluate_steps_sparse(self, make_scanner, parsed_string):
        scanner = make_scanner('Scan1D', 'Sparse')
        scanner.settings['parsed_string'] = parsed_string
        assert_steps_consistent(scanner)
