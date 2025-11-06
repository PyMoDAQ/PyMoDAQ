import numbers
from typing import Union

import numpy
import numpy as np
from numbers import Number
from typing import List, Union, Tuple
from pymodaq_utils.logger import get_module_name, set_logger
from collections.abc import Iterable
from pint import Quantity

logger = set_logger(get_module_name(__file__))


def my_moment(x, y):
    """Returns the moments of a distribution y over an axe x

    Parameters
    ----------
    x: list or ndarray
       vector of floats
    y: list or ndarray
       vector of floats corresponding to the x axis

    Returns
    -------
    m: list
       Contains moment of order 0 (mean) and of order 1 (std) of the distribution y
    """
    dx = np.mean(np.diff(x))
    norm = np.sum(y) * dx
    m = [np.sum(x * y) * dx / norm]
    m.extend([np.sqrt(np.sum((x - m[0]) ** 2 * y) * dx / norm)])
    return m


def normalize(x):
    x = x - np.min(x)
    x = x / np.max(x)
    return x


def normalize_to(array: np.ndarray, value: numbers.Number):
    return normalize(array) * value


def odd_even(x: Union[int, np.ndarray]):
    """
    odd_even tells if a number (or an array) is odd (return True) or even (return False)

    Parameters
    ----------
    x: the integer number (or array) to test

    Returns
    -------
    bool : boolean or array of boolean
    """
    if not (isinstance(x, int) or (isinstance(x, np.ndarray) and x.dtype == int)):
        raise TypeError(f'{x} should be an integer or an array of integers')
    if isinstance(x, int):
        if x % 2 == 0:
            isodd = False
        else:
            isodd = True
    else:
        isodd = x % 2 != 0
    return isodd


def greater2n(x):
    """
    return the first power of 2 greater than x
    Parameters
    ----------
    x: (int or float) a number

    Returns
    -------
    int: the power of 2 greater than x
    """
    if isinstance(x, bool):
        raise TypeError(f'{x} should be an integer or a float')
    if hasattr(x, '__iter__'):
        res = []
        for el in x:
            if isinstance(el, bool):
                raise TypeError(f'{el} should be an integer or a float')
            if not (isinstance(el, int) or isinstance(el, float)):
                raise TypeError(f'{x} elements should be integer or float')
            res.append(1 << (int(el) - 1).bit_length())
        if isinstance(x, np.ndarray):
            return np.array(res)
        else:
            return res
    else:
        if not (isinstance(x, int) or isinstance(x, float)):
            raise TypeError(f'{x} should be an integer or a float')
        return 1 << (int(x) - 1).bit_length()


def wrap(input: Union[np.ndarray, float], phase_range=(0, 2*np.pi)):
    return (input - phase_range[0]) % (phase_range[1]-phase_range[0]) + phase_range[0]


def linspace_step(start, stop, step):
    """
    Compute a regular linspace_step distribution from start to stop values.

    =============== =========== ======================================
    **Parameters**    **Type**    **Description**
    *start*            scalar      the starting value of distribution
    *stop*             scalar      the stopping value of distribution
    *step*             scalar      the length of a distribution step
    =============== =========== ======================================

    Returns
    -------

    scalar array
        The computed distribution axis as an array.
    """
    if np.sign(stop - start) != np.sign(step) or start == stop:
        raise ValueError('Invalid value for one parameter')
    Nsteps = int(np.ceil((stop - start) / step))
    new_stop = start + (Nsteps - 1) * step
    if isinstance(new_stop, Quantity):
        tol = (new_stop + step - stop).magnitude
    else:
        tol = (new_stop + step - stop)
    if np.abs(tol) < 1e-12:
        Nsteps += 1
    new_stop = start + (Nsteps - 1) * step
    return np.linspace(start, new_stop, Nsteps)


def linspace_step_N(start, step, Npts):
    stop = (Npts - 1) * step + start
    return linspace_step(start, stop, step)


def find_index(x, threshold: Union[Number, List[Number]]) -> List[tuple]:
    """find_index finds the index ix such that x(ix) is the closest from threshold

    Parameters
    ----------
    x : vector
    threshold : list of real numbers

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    """

    if not hasattr(threshold, '__iter__'):
        threshold = [threshold]
    out = []
    for value in threshold:
        ix = int(np.argmin(np.abs(x - value)))
        out.append((ix, x[ix]))
    return out


def find_common_index(x: Iterable, y: Iterable, x0: Number, y0: Number) -> Tuple:
    """find the index in two vectors corresponding to x0 and y0"""
    vals = x + 1j * y
    val = x0 + 1j * y0
    ind = int(np.argmin(np.abs(vals - val)))
    return ind, x[ind], y[ind]


def gauss1D(x, x0, dx, n=1):
    """
    compute the gaussian function along a vector x, centered in x0 and with a
    FWHM i intensity of dx. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian

    Parameters
    ----------
    x: (ndarray) first axis of the 2D gaussian
    x0: (float) the central position of the gaussian
    dx: (float) :the FWHM of the gaussian
    n=1 : an integer to define hypergaussian, n=1 by default for regular gaussian
    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis

    """
    if dx <= 0:
        raise ValueError('dx should be strictly positive')
    if not isinstance(n, int):
        raise TypeError('n should be a positive integer')
    elif n < 0:
        raise ValueError('n should be a positive integer')
    out = np.exp(-2 * np.log(2) ** (1 / n) * (((x - x0) / dx)) ** (2 * n))
    return out


def gauss2D(x, x0, dx, y, y0, dy, n=1, angle=0):
    """
    compute the 2D gaussian function along a vector x, centered in x0 and with a
    FWHM in intensity of dx and smae along y axis. n=1 is for the standard gaussian while n>1 defines
    a hypergaussian. optionally rotate it by an angle in degree

    Parameters
    ----------
    x: (ndarray) first axis of the 2D gaussian
    x0: (float) the central position of the gaussian
    dx: (float) :the FWHM of the gaussian
    y: (ndarray) second axis of the 2D gaussian
    y0: (float) the central position of the gaussian
    dy: (float) :the FWHM of the gaussian
    n=1 : an integer to define hypergaussian, n=1 by default for regular gaussian
    angle: (float) a float to rotate main axes, in degree

    Returns
    -------
    out : ndarray 2 dimensions

    """
    if angle == 0:
        data = np.transpose(np.outer(gauss1D(x, x0, dx, n), gauss1D(y, y0, dy, n)))

    else:

        theta = np.radians(angle)
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c, -s), (s, c)))
        (x0r, y0r) = tuple(R.dot(np.array([x0, y0])))

        data = np.zeros((len(y), len(x)))

        for indx, xtmp in enumerate(x):
            for indy, ytmp in enumerate(y):
                rotatedvect = R.dot(np.array([xtmp, ytmp]))
                data[indy, indx] = gauss1D(rotatedvect[0], x0r, dx, n) * gauss1D(rotatedvect[1], y0r, dy, n)

    return data


def rotate2D(origin:tuple = (0,0), point:tuple = (0,0), angle:float = 0):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    Parameters
    ----------
    origin: (tuple) x,y coordinate from which to rotate
    point: (tuple) x,y coordinate of point to rotate
    angle: (float) a float to rotate main axes, in radian

    Returns
    -------
    out : (tuple) x,y coordinate of rotated point

    """    
    ox, oy = origin
    px, py = point

    qx = ox + np.cos(angle) * (px - ox) - np.sin(angle) * (py - oy)
    qy = oy + np.sin(angle) * (px - ox) + np.cos(angle) * (py - oy)
    return qx, qy

def ftAxis(Npts, omega_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts: (int)
      A number of points defining the length of both grids
    omega_max: (float)
      The maximum circular frequency in the spectral domain. its unit defines
      the temporal units. ex: omega_max in rad/fs implies time_grid in fs

    Returns
    -------
    omega_grid: (ndarray)
      The spectral axis of the FFT
    time_grid: (ndarray))
      The temporal axis of the FFT
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(Npts, int):
        raise TypeError('n should be a positive integer, if possible power of 2')
    elif Npts < 1:
        raise ValueError('n should be a strictly positive integer')
    dT = 2 * np.pi / (2 * omega_max)
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ftAxis_time(Npts, time_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts : number
      A number of points defining the length of both grids
    time_max : number
      The maximum tmporal window

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT
    time_grid : vector
      The temporal axis of the FFT
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(Npts, int):
        raise TypeError('n should be a positive integer, if possible power of 2')
    elif Npts < 1:
        raise ValueError('n should be a strictly positive integer')
    dT = time_max / Npts
    omega_max = (Npts - 1) / 2 * 2 * np.pi / time_max
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ft(x, dim=-1):
    """
    Process the 1D fast fourier transform and swaps the axis to get coorect results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(dim, int):
        raise TypeError('dim should be an integer specifying the array dimension over which to do the calculation')
    assert isinstance(x, np.ndarray)
    assert dim >= -1
    assert dim <= len(x.shape) - 1

    out = np.fft.fftshift(np.fft.fft(np.fft.fftshift(x, axes=dim), axis=dim), axes=dim)
    return out


def ift(x, dim=0):
    """
    Process the inverse 1D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(dim, int):
        raise TypeError('dim should be an integer specifying the array dimension over which to do the calculation')
    assert isinstance(x, np.ndarray)
    assert dim >= -1
    assert dim <= len(x.shape) - 1
    out = np.fft.fftshift(np.fft.ifft(np.fft.fftshift(x, axes=dim), axis=dim), axes=dim)
    return out


def ft2(x, dim=(-2, -1)):
    """
    Process the 2D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    assert isinstance(x, np.ndarray)
    if hasattr(dim, '__iter__'):
        for d in dim:
            if not isinstance(d, int):
                raise TypeError(
                    'elements in dim should be an integer specifying the array dimension over which to do the calculation')
            assert d <= len(x.shape)
    else:
        if not isinstance(dim, int):
            raise TypeError(
                'elements in dim should be an integer specifying the array dimension over which to do the calculation')
        assert dim <= len(x.shape)
    out = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out


def ift2(x, dim=(-2, -1)):
    """
    Process the inverse 2D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis (or a tuple of axes) over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    assert isinstance(x, np.ndarray)
    if hasattr(dim, '__iter__'):
        for d in dim:
            if not isinstance(d, int):
                raise TypeError(
                    'elements in dim should be an integer specifying the array dimension over which to do the calculation')
            assert d <= len(x.shape)
    else:
        if not isinstance(dim, int):
            raise TypeError(
                'elements in dim should be an integer specifying the array dimension over which to do the calculation')
        assert dim <= len(x.shape)
    out = np.fft.fftshift(np.fft.ifft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out


def flatten(xs):
    """Flatten nested list"""
    for x in xs:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            yield from flatten(x)
        else:
            yield x

class LSqEllipse:

    def fit(self, data):
        """Lest Squares fitting algorithm

        Theory taken from (*)
        Solving equation Sa=lCa. with a = |a b c d f g> and a1 = |a b c>
            a2 = |d f g>

        Args
        ----
        data (list:list:float): list of two lists containing the x and y data of the
            ellipse. of the form [[x1, x2, ..., xi],[y1, y2, ..., yi]]

        Returns
        ------
        coef (list): list of the coefficients describing an ellipse
           [a,b,c,d,f,g] corresponding to ax**2+2bxy+cy**2+2dx+2fy+g
        """
        x, y = numpy.asarray(data, dtype=float)

        # Quadratic part of design matrix [eqn. 15] from (*)
        D1 = numpy.mat(numpy.vstack([x ** 2, x * y, y ** 2])).T
        # Linear part of design matrix [eqn. 16] from (*)
        D2 = numpy.mat(numpy.vstack([x, y, numpy.ones(len(x))])).T

        # forming scatter matrix [eqn. 17] from (*)
        S1 = D1.T * D1
        S2 = D1.T * D2
        S3 = D2.T * D2

        # Constraint matrix [eqn. 18]
        C1 = numpy.mat('0. 0. 2.; 0. -1. 0.; 2. 0. 0.')

        # Reduced scatter matrix [eqn. 29]
        M = C1.I * (S1 - S2 * S3.I * S2.T)

        # M*|a b c >=l|a b c >. Find eigenvalues and eigenvectors from this equation [eqn. 28]
        eval, evec = numpy.linalg.eig(M)

        # eigenvector must meet constraint 4ac - b^2 to be valid.
        cond = 4 * numpy.multiply(evec[0, :], evec[2, :]) - numpy.power(evec[1, :], 2)
        a1 = evec[:, numpy.nonzero(cond.A > 0)[1]]

        # |d f g> = -S3^(-1)*S2^(T)*|a b c> [eqn. 24]
        a2 = -S3.I * S2.T * a1

        # eigenvectors |a b c d f g>
        self.coef = numpy.vstack([a1, a2])
        self._save_parameters()

    def _save_parameters(self):
        """finds the important parameters of the fitted ellipse

        Theory taken form http://mathworld.wolfram

        Args
        -----
        coef (list): list of the coefficients describing an ellipse
           [a,b,c,d,f,g] corresponding to ax**2+2bxy+cy**2+2dx+2fy+g

        Returns
        _______
        center (List): of the form [x0, y0]
        width (float): major axis
        height (float): minor axis
        phi (float): rotation of major axis form the x-axis in radians
        """

        # eigenvectors are the coefficients of an ellipse in general form
        # a*x^2 + 2*b*x*y + c*y^2 + 2*d*x + 2*f*y + g = 0 [eqn. 15) from (**) or (***)
        a = self.coef[0, 0]
        b = self.coef[1, 0] / 2.
        c = self.coef[2, 0]
        d = self.coef[3, 0] / 2.
        f = self.coef[4, 0] / 2.
        g = self.coef[5, 0]

        # finding center of ellipse [eqn.19 and 20] from (**)
        x0 = (c * d - b * f) / (b ** 2. - a * c)
        y0 = (a * f - b * d) / (b ** 2. - a * c)

        # Find the semi-axes lengths [eqn. 21 and 22] from (**)
        numerator = 2 * (a * f * f + c * d * d + g * b * b - 2 * b * d * f - a * c * g)
        denominator1 = (b * b - a * c) * ((c - a) * numpy.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
        denominator2 = (b * b - a * c) * ((a - c) * numpy.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
        width = numpy.sqrt(numerator / denominator1)
        height = numpy.sqrt(numerator / denominator2)

        # angle of counterclockwise rotation of major-axis of ellipse to x-axis [eqn. 23] from (**)
        # or [eqn. 26] from (***).
        phi = .5 * numpy.arctan((2. * b) / (a - c))

        self._center = [x0, y0]
        self._width = width
        self._height = height
        self._phi = phi

    @property
    def center(self):
        return self._center

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def phi(self):
        """angle of counterclockwise rotation of major-axis of ellipse to x-axis
        [eqn. 23] from (**)
        """
        return self._phi

    def parameters(self):
        return self.center, self.width, self.height, self.phi


def make_test_ellipse(center=[1, 1], width=1, height=.6, phi=3.14 / 5):
    """Generate Elliptical data with noise

    Args
    ----
    center (list:float): (<x_location>, <y_location>)
    width (float): semimajor axis. Horizontal dimension of the ellipse (**)
    height (float): semiminor axis. Vertical dimension of the ellipse (**)
    phi (float:radians): tilt of the ellipse, the angle the semimajor axis
        makes with the x-axis

    Returns
    -------
    data (list:list:float): list of two lists containing the x and y data of the
        ellipse. of the form [[x1, x2, ..., xi],[y1, y2, ..., yi]]
    """
    t = numpy.linspace(0, 2 * numpy.pi, 1000)
    x_noise, y_noise = numpy.random.rand(2, len(t))

    ellipse_x = center[0] + width * numpy.cos(t) * numpy.cos(phi) - height * numpy.sin(t) * numpy.sin(
        phi) + x_noise / 2.
    ellipse_y = center[1] + width * numpy.cos(t) * numpy.sin(phi) + height * numpy.sin(t) * numpy.cos(
        phi) + y_noise / 2.

    return [ellipse_x, ellipse_y]

