# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import numpy as np

Cb = 1.602176e-19  # coulomb
h = 6.626068e-34  # J.s
c = 2.997924586e8  # m.s-1


def Enm2cmrel(E_nm, ref_wavelength=515):
    """Converts energy in nm to cm-1 relative to a ref wavelength

    Parameters
    ----------
    E_nm: float
          photon energy in wavelength (nm)
    ref_wavelength: float
                    reference wavelength in nm from which calculate the photon relative energy

    Returns
    -------
    float
         photon energy in cm-1 relative to the ref wavelength

    Examples
    --------
    >>> Enm2cmrel(530, 515)
    549.551199853453
    """
    return 1 / (ref_wavelength * 1e-7) - 1 / (E_nm * 1e-7)


def Ecmrel2Enm(Ecmrel, ref_wavelength=515):
    """Converts energy from cm-1 relative to a ref wavelength to an energy in wavelength (nm)

    Parameters
    ----------
    Ecmrel: float
            photon energy in cm-1
    ref_wavelength: float
                    reference wavelength in nm from which calculate the photon relative energy

    Returns
    -------
    float
         photon energy in nm

    Examples
    --------
    >>> Ecmrel2Enm(500, 515)
    528.6117526302285
    """
    Ecm = 1 / (ref_wavelength * 1e-7) - Ecmrel
    return 1 / (Ecm * 1e-7)


def eV2nm(E_eV):
    """Converts photon energy from electronvolt to wavelength in nm

    Parameters
    ----------
    E_eV: float
          Photon energy in eV

    Returns
    -------
    float
         photon energy in nm

    Examples
    --------
    >>> eV2nm(1.55)
    799.898112990037
    """
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_nm = c / E_freq * 1e9
    return E_nm


def nm2eV(E_nm):
    """Converts photon energy from wavelength in nm to electronvolt

    Parameters
    ----------
    E_nm: float
          Photon energy in nm

    Returns
    -------
    float
         photon energy in eV

    Examples
    --------
    >>> nm2eV(800)
    1.549802593918197
    """
    E_freq = c / E_nm * 1e9
    E_J = E_freq * h
    E_eV = E_J / Cb
    return E_eV


def E_J2eV(E_J):
    E_eV = E_J / Cb
    return E_eV


def eV2cm(E_eV):
    """Converts photon energy from electronvolt to absolute cm-1

    Parameters
    ----------
    E_eV: float
          Photon energy in eV

    Returns
    -------
    float
         photon energy in cm-1

    Examples
    --------
    >>> eV2cm(0.07)
    564.5880342655984
    """
    E_nm = eV2nm(E_eV)
    E_cm = 1 / (E_nm * 1e-7)
    return E_cm


def nm2cm(E_nm):
    """Converts photon energy from wavelength to absolute cm-1

        Parameters
        ----------
        E_nm: float
              Photon energy in nm

        Returns
        -------
        float
             photon energy in cm-1

        Examples
        --------
        >>> nm2cm(0.04)
        0.000025
        """
    return 1 / (E_nm * 1e7)


def cm2nm(E_cm):
    """Converts photon energy from absolute cm-1 to wavelength

            Parameters
            ----------
            E_cm: float
                  photon energy in cm-1

            Returns
            -------
            float
                 Photon energy in nm

            Examples
            --------
            >>> cm2nm(1e5)
            100
            """
    return 1 / (E_cm * 1e-7)


def eV2E_J(E_eV):
    E_J = E_eV * Cb
    return E_J


def eV2radfs(E_eV):
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_radfs = E_freq * 2 * np.pi / 1e15
    return E_radfs


def l2w(x, speedlight=300):
    """Converts photon energy in rad/fs to nm (and vice-versa)

    Parameters
    ----------
    x: float
       photon energy in wavelength or rad/fs
    speedlight: float, optional
                the speed of light, by default 300 nm/fs

    Returns
    -------
    float

    Examples
    --------
    >>> l2w(800)
    2.356194490192345
    >>> l2w(800,3e8)
    2356194.490192345
    """
    y = 2 * np.pi * speedlight / x
    return y



