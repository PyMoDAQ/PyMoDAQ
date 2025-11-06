# -*- coding: utf-8 -*-
"""
Created on Mon March 03 2021
author: Sebastien Weber
"""
import numpy as np


def random_step(start, stop, step):
    tmp = start
    out = np.array([tmp])
    sign = stop - start
    if step == 0:
        raise ValueError('step must be strictly positive or negative')
    if step > 0 and sign > 0:
        while tmp <= stop:
            tmp = tmp + (np.random.random() + 0.5) * step
            out = np.append(out, tmp)
    elif step < 0 and sign < 0:
        while tmp >= stop:
            tmp = tmp + (np.random.random() + 0.5) * step
            out = np.append(out, tmp)
    else:
        raise ValueError(f'the step value {step} is not of the same sign as stop - start : {sign}')
    return out[0:-1]


def linspace_this_vect(x, y=None, Npts=None):
    """
        Given a vector x, it returns a vector xlin where xlin is a
        linearised version of x on the same interval and with the same size.
        if args is provided it is a y vector and the function returns both xlin
        and ylin where ylin is a linear interpolation of y on this new xlin axis
    
        Parameters
        ----------
        x : (ndarray)
        y : (ndarray) optional
        Npts: (int) size of the linear vector (optional)

        Returns
        -------
        xlin : vector
        (ylin : vector) optional if args is provided

    """
    if not Npts:
        Npts = np.size(x)
    xlin = np.linspace(np.min(x), np.max(x), Npts)
    if y is not None:
        ylin = np.interp(xlin, x, y)
        return xlin, ylin
    else:
        return xlin

    
def find_index(x, threshold):
    """
    find_index finds the index ix such that x(ix) is the closest from threshold
    
    Parameters
    ----------
    x : vector
    threshold : list of scalar

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    """

    if np.isscalar(threshold):
        threshold = [threshold]
    out = []
    for value in threshold:
        ix = int(np.argmin(np.abs(x - value)))
        out.append((ix, x[ix]))
    return out


def find_rising_edges(x, threshold):
    """find_rising_edges finds the index ix such that x(ix) is the closest from threshold and values are increasing
    
    Parameters
    ----------
    x : vector
    threshold : list of scalar

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    
    """
    x_shifted = np.concatenate((x[1:], np.array((np.nan,))))
    if np.isscalar(threshold):
        threshold = [threshold]
    out = []
    for value in threshold:
        dat = np.bitwise_and(x < value, x_shifted > value)
        ix = [ind for ind, flag in enumerate(dat) if flag]
        out.append((ix, x[ix]))
    return out


def crop_vector_to_axis(x, V, xlim):
    """crops a vector V with given x axis vector to a given xlim tuple
    
    Parameters
    ----------
    x : vector
    V : vector
    xlim: tuple containing (xmin,xmax)
    
    Returns
    -------
    x_c : vector
    V_c : vector
    """
    x1 = find_index(x, xlim[0])[0][0]
    x2 = find_index(x, xlim[1])[0][0]
    if x2 > x1:
        ixx = np.linspace(x1, x2, x2 - x1 + 1, dtype=int);
    else:
        ixx = np.linspace(x2, x1, x1 - x2 + 1, dtype=int);

    x_c = x[ixx]
    V_c = V[ixx]
    return x_c, V_c

def rescale(x, window=[0.0, 1.0]):
    """ Rescales a numpy array to the range specified by ``window``.

    Default is [0, 1].
    """
    maxx = np.max(x)
    minx = np.min(x)
    return (x - minx) / (maxx - minx) * (window[1] - window[0]) + window[0]


def marginals(data, normalize=False, axes=None):
    """ Calculates the marginals of the data array.

    axes specifies the axes of the marginals, e.g., the axes on which the
    sum is projected.

    If axis is None a list of all marginals is returned.
    """
    if axes is None:
        axes = range(data.ndim)
    axes = list(axes)
    full_axes = list(range(data.ndim))
    m = []
    for i in axes:
        # for the marginal sum over all axes except the specified one
        margin_axes = tuple(j for j in full_axes if j != i)
        m.append(np.sum(data, axis=margin_axes))
    if normalize:
        m = [rescale(mx) for mx in m]
    return tuple(m) if len(m) != 1 else m[0]


def find(x, condition, n=1):
    """ Return the index of the nth element that fulfills the condition.
    """
    search_n = 1
    for i in range(len(x)):
        if condition(x[i]):
            if search_n == n:
                return i
            search_n += 1
    return -1


def arglimit(y, threshold=1e-3, padding=0.0, normalize=True):
    """ Returns the first and last index where `y >= threshold * max(abs(y))`.
    """
    t = np.abs(y)
    if normalize:
        t = t / np.max(t)

    idx1 = find(t, lambda x: x >= threshold)
    if idx1 == -1:
        idx1 = 0
    idx2 = find(t[::-1], lambda x: x >= threshold)
    if idx2 == -1:
        idx2 = t.shape[0] - 1
    else:
        idx2 = t.shape[0] - 1 - idx2

    return (idx1, idx2)


def limit(x, y=None, threshold=1e-3, padding=0.25, extend=True):
    """ Returns the maximum x-range where the y-values are sufficiently large.

    Parameters
    ----------
    x : array_like
        The x values of the graph.
    y : array_like, optional
        The y values of the graph. If `None` the maximum range of `x` is
        used. That is only useful if `padding > 0`.
    threshold : float
        The threshold relative to the maximum of `y` of values that should be
        included in the bracket.
    padding : float
        The relative padding on each side in fractions of the bracket size.
    extend : bool, optional
        Signals if the returned range can be larger than the values in ``x``.
        Default is `True`.

    Returns
    -------
    xl, xr : float
        Lowest and biggest value of the range.

    """
    if y is None:
        x1, x2 = np.min(x), np.max(x)
        if not extend:
            return (x1, x2)
    else:
        idx1, idx2 = arglimit(y, threshold=threshold)
        x1, x2 = sorted([x[idx1], x[idx2]])

    # calculate the padding
    if padding != 0.0:
        pad = (x2 - x1) * padding
        x1 -= pad
        x2 += pad

    if not extend:
        x1 = max(x1, np.min(x))
        x2 = min(x2, np.max(x))

    return (x1, x2)


def crop_array_to_axis(x, y, M, cropbox):
    """crops an array M with given cropbox as a tuple (xmin,xmax,ymin,ymax).
    
    Parameters
    ----------
    x : vector
    y : vector
    M : 2D array
    cropbox: 4 elements tuple containing (xmin,xmax,ymin,ymax)
    
    Returns
    -------
    x_c : croped x vector
    y_c : croped y  vector
    M_c : croped 2D M array

    """
    x1 = find_index(x, cropbox[0])[0][0]
    x2 = find_index(x, cropbox[1])[0][0]
    if x2 > x1:
        ixx = np.linspace(x1, x2, x2 - x1 + 1, dtype=int)
    else:
        ixx = np.linspace(x2, x1, x1 - x2 + 1, dtype=int)

    y1 = find_index(y, cropbox[2])[0][0]
    y2 = find_index(y, cropbox[3])[0][0]
    if y2 > y1:
        iyy = np.linspace(y1, y2, y2 - y1 + 1, dtype=int)
    else:
        iyy = np.linspace(y2, y1, y1 - y2 + 1, dtype=int)

    x_c = x[ixx]
    y_c = y[iyy]

    M_c = M[iyy[0]:iyy[-1] + 1, ixx[0]:ixx[-1] + 1]
    return x_c, y_c, M_c


def interp1D(x, M, xlin, axis=1):
    """
    same as numpy interp function but works on 2D array
    you have to specify the axis over which to do the interpolation
    kwargs refers to the numpy interp kwargs
    returns both xlin and the new 2D array Minterp
    """
    if axis == 0:
        Minterp = np.zeros((np.size(xlin), np.size(M, axis=1)))
        indexes = np.arange(0, np.size(M, axis=1))
        for ind in indexes:
            #             print(ind)
            Minterp[:, ind] = np.interp(xlin, x, M[:, ind])
    else:
        Minterp = np.zeros((np.size(M, axis=0), np.size(xlin)))
        indexes = np.arange(0, np.size(M, axis=0))
        for ind in indexes:
            Minterp[ind, :] = np.interp(xlin, x, M[ind, :])
    return Minterp


def linspace_this_image(x, M, axis=1, Npts=None):
    """
    Given a vector x and a 2D array M, it returns an array vector xlin where xlin is a
    linearised version of x on the same interval and with the same size. it returns as well
    a 2D array Minterp interpolated on the new xlin vector along the specified axis.

    Parameters
    ----------
    x : (vector)
    M : (2D array)
    axis : (int)
    Npts: (int) size of the linear vector (optional)

    Returns
    -------
    xlin : vector
    Minterp : 2D array
    """
    xlin = linspace_this_vect(x, Npts=Npts)
    Minterp = interp1D(x, M, xlin, axis=axis)

    return xlin, Minterp


def max_ind(x, axis=None):
    """returns the max value in a vector or array and its index (in a tuple)

    Parameters
    ----------
    x : vector
    
    axis : optional dimension aginst which to normalise
      
    Returns
    -------
    ind_max : index of the maximum value
    
    max_val : maximum value
    """
    ind_max = np.argmax(x, axis=axis)
    max_val = np.max(x, axis=axis)
    return ind_max, max_val


def min_ind(x, axis=None):
    """returns the min value in a vector or array and its index (in flattened array)

    Parameters
    ----------
    x : vector
    axis : optional dimension to check the function

    Returns
    -------
    ind_min : index of the minimum value
    min_val : minimum value
    """
    ind_min = np.argmin(x, axis=axis)
    min_val = np.min(x, axis=axis)
    return ind_min, min_val


if __name__ == '__main__':                                          # pragma: no cover
    from pymodaq.utils import daq_utils as utils
    import matplotlib.pyplot as plt

    x = random_step(00, 100, 5)
    y = random_step(00, 100, 5)
    g2 = utils.gauss2D(x, 35, 15, y, 55, 20, 1)
    (xlin, g2_interp) = linspace_this_image(x, g2, axis=1, Npts=100)
    (ylin, g2_interp_both) = linspace_this_image(y, g2_interp, axis=0, Npts=100)
    plt.figure('gauss2D')
    plt.subplot(221)
    plt.pcolormesh(x, y, g2)
    plt.subplot(222)
    plt.pcolormesh(xlin, y, g2_interp)
    plt.subplot(223)
    plt.pcolormesh(xlin, ylin, g2_interp_both)

    plt.show()

    x_c, y_c, M_c = crop_array_to_axis(x, y, g2, [20, 60, 40, 80])
    plt.figure('cropped')
    plt.subplot(121)
    plt.pcolormesh(x, y, g2)
    plt.subplot(122)
    plt.pcolormesh(x_c, y_c, M_c)
    plt.show()
