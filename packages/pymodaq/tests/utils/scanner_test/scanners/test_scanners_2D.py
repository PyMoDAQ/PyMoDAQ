# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
import pytest

from .conftest import assert_steps_consistent

# (start1, stop1, step1), (start2, stop2, step2)
linear_conditions = [
    ((0., 1., 0.1), (0., 1., 0.1)),
    ((0., 1., 0.3), (0., 1., 0.25)),
    ((0., 1., 0.7), (0., 2., 0.5)),
    ((0., 1., 1 / 3), (0., 1., 1 / 7)),
    ((0., 10., 1.), (0., 5., 1.)),
    ((0., 1., 0.01), (0., 1., 0.1)),
    ((-1., 1., 0.2), (-5.3, 7.1, 0.37)),
    ((1., 0., -0.1), (0., 1., 0.1)),
    ((1., -1., -0.3), (3., 0., -0.7)),
    ((0., 0.7, 0.1), (0., 0.7, 0.1)),
    ((0., 1., 2.), (0., 1., 2.)),  # steps larger than the ranges
]

invalid_linear_conditions = [
    ((0., 1., -0.1), (0., 1., 0.1)),  # wrong step sign
    ((0., 1., 0.), (0., 1., 0.1)),  # null step
    ((0., 0., 0.1), (0., 1., 0.1)),  # start == stop
    ((0., 1., 0.1), (0., 1., -0.1)),  # one valid axis, one invalid
]

spiral_conditions = [(2, 1., 1.), (5, 5., 3.), (10, 5., 5.), (10, 2.5, 7.), (4, 1., 2.), (1, 1., 1.), (20, 3., 1.)]


def set_linear(scanner, conditions):
    for ind, (start, stop, step) in enumerate(conditions, start=1):
        scanner.settings['axis%d' % ind, 'start_axis%d' % ind] = start
        scanner.settings['axis%d' % ind, 'stop_axis%d' % ind] = stop
        scanner.settings['axis%d' % ind, 'step_axis%d' % ind] = step


class TestScanner2D:
    @pytest.mark.parametrize('subtype', ['Linear', 'LinearBackForce', 'Random', 'RandomSpread'])
    @pytest.mark.parametrize('conditions', linear_conditions)
    def test_evaluate_steps_linear(self, make_scanner, subtype, conditions):
        scanner = make_scanner('Scan2D', subtype, n_act=2)
        set_linear(scanner, conditions)
        assert_steps_consistent(scanner)

    @pytest.mark.parametrize('subtype', ['Linear', 'LinearBackForce', 'Random', 'RandomSpread'])
    @pytest.mark.parametrize('conditions', invalid_linear_conditions)
    def test_evaluate_steps_linear_invalid(self, make_scanner, subtype, conditions):
        """With invalid settings the scan degenerates to a single point"""
        scanner = make_scanner('Scan2D', subtype, n_act=2)
        set_linear(scanner, conditions)
        assert_steps_consistent(scanner)
        assert scanner.n_steps == 1

    @pytest.mark.parametrize('npts, rmax1, rmax2', spiral_conditions)
    def test_evaluate_steps_spiral(self, make_scanner, npts, rmax1, rmax2):
        scanner = make_scanner('Scan2D', 'Spiral', n_act=2)
        scanner.settings['npts_by_axis'] = npts
        scanner.settings['axis1', 'rmax_axis1'] = rmax1
        scanner.settings['axis2', 'rmax_axis2'] = rmax2
        assert_steps_consistent(scanner)
