# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import pytest

from pymodaq.utils import units


class TestUnits:

    def test_Enm2cmrel(self):
        assert units.Enm2cmrel(520, 515) == pytest.approx(186.70649738)

    def test_Ecmrel2Enm(self):
        assert units.Ecmrel2Enm(500, 515) == pytest.approx(528.6117526)

    def test_eV2nm(self):
        assert units.eV2nm(1.55) == pytest.approx(799.89811299)

    def test_nm2eV(self):
        assert units.nm2eV(800) == pytest.approx(1.54980259)

    def test_E_J2eV(self):
        assert units.E_J2eV(1e-18) == pytest.approx(6.24151154)

    def test_eV2cm(self):
        assert units.eV2cm(0.07) == pytest.approx(564.5880342655)

    def test_nm2cm(self):
        assert units.nm2cm(0.04) == pytest.approx(0.0000025)

    def test_cm2nm(self):
        assert units.cm2nm(1e5) == pytest.approx(100)

    def test_eV2E_J(self):
        assert units.eV2E_J(800) == pytest.approx(1.2817408e-16)

    def test_eV2radfs(self):
        assert units.eV2radfs(1.55) == pytest.approx(2.3548643)

    def test_l2w(self):
        assert units.l2w(800) == pytest.approx(2.35619449)

