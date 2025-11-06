from typing import Union, List, TYPE_CHECKING, Iterable, Optional, Callable
import numbers
from copy import deepcopy

import numpy as np
from pint.facets.numpy.numpy_func import HANDLED_UFUNCS  # imported by the data module
from pymodaq_data import Q_
from pymodaq_data import data as data_mod

from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq_data.data import DataBase, DataWithAxes

HANDLED_FUNCTIONS = {}

logger = set_logger(get_module_name(__file__))


def process_arguments_for_ufuncs(input: 'DataBase',
                      inputs: List[Union[numbers.Number, Q_, np.ndarray, 'DataBase']]):
    """

    Parameters
    ----------
    input: 'DataBase'
    inputs: list of elts in a numpy operation, could be numbers, quantities, ndarray, or 'DataBase'

    Returns
    -------
    list of numbers, quantities or numpy arrays for applying to pint handled functions
    """
    elts = []
    for elt in inputs:
        if isinstance(elt, numbers.Number):
            elts.append([elt for _ in range(input.length)])
        elif isinstance(elt, Q_):  # take its magnitude
            elts.append([elt for _ in range(input.length)])
        elif isinstance(elt, np.ndarray):
            if elt.size != input.size:
                raise TypeError("inconsistent sizes")
            elts.append([elt for _ in range(input.length)])
        else:
            try:
                elts.append([Q_(array, elt.units) for array in elt.data])
            except:
                return NotImplementedError
    return elts


def implements(np_function):
    """Register an __array_function__ implementation for DataWithAxes."""
    def decorator(func):
        HANDLED_FUNCTIONS[np_function] = func
        return func
    return decorator

# ********* FUNCTIONS that reduce dimensions *****************

def process_with_reduced_dimensions(func: Callable, dwa: 'DataWithAxes',
                                    axis: Optional[Union[int, Iterable[int]]] = None,
                                    *args, **kwargs):
    all_axes = list(dwa.nav_indexes) + list(dwa.sig_indexes)
    if axis is None:
        remove_axis = all_axes
    elif isinstance(axis, int):
        remove_axis = all_axes[axis]
    else:
        remove_axis = [all_axes[axis_index] for axis_index in axis]
    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.atleast_1d(func(dwa.data[ind], axis, *args, **kwargs)) for ind in range(len(dwa))],
        remove_axes_index=remove_axis
    )
    dwa_func.name += f'_{func.__name__}'
    return dwa_func


@implements('max')
def _max(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.max, dwa, *args, axis=axis, **kwargs)


@implements('min')
def _min(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.min, dwa, *args, axis=axis, **kwargs)


@implements('argmax')
def _argmax(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.argmax, dwa, *args, axis=axis, **kwargs)


@implements('argmin')
def _argmin(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.argmin, dwa, *args, axis=axis, **kwargs)

@implements("std")
def _std(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.std, dwa, *args, axis=axis, **kwargs)


@implements("mean")
def _mean(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.mean, dwa, *args, axis=axis, **kwargs)


@implements("sum")
def _sum(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.sum, dwa, *args, axis=axis, **kwargs)


# ************* FUNCTIONS that apply with units ********

@implements('angle')
def _angle(dwa: 'DataWithAxes', *args, **kwargs):

    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.angle(array, *args, **kwargs) for array in dwa.data])
    dwa_func.name += f"_{'angle'}"
    return dwa_func


@implements('unwrap')
def _unwrap(dwa: 'DataWithAxes', *args, **kwargs):
    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.unwrap(array, *args, **kwargs) for array in dwa.data])
    dwa_func.name += f"_{'unwrap'}"
    return dwa_func


@implements('real')
def _real(dwa: 'DataWithAxes', *args, **kwargs):

    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.real(array, *args, **kwargs) for array in dwa.data])
    dwa_func.name += f"_{'real'}"
    return dwa_func


@implements('imag')
def _imag(dwa: 'DataWithAxes', *args, **kwargs):

    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.imag(array, *args, **kwargs) for array in dwa.data])
    dwa_func.name += f"_{'imag'}"
    return dwa_func


@implements('absolute')
def _absolute(dwa: 'DataWithAxes', *args, **kwargs):

    dwa_func = dwa.deepcopy_with_new_data(
        data=[np.absolute(array, *args, **kwargs) for array in dwa.data])
    dwa_func.name += f"_{'absolute'}"
    return dwa_func


@implements('abs')
def _abs(dwa: 'DataWithAxes', *args, **kwargs):
    return np.absolute(dwa, *args, **kwargs)


@implements('roll')
def _roll(dwa: 'DataWithAxes', *args, **kwargs):
    dwa_func = dwa.deepcopy_with_new_data(data=[np.roll(array, *args, **kwargs) for array in dwa])
    dwa_func.name += f"_{'roll'}"
    return dwa_func


@implements('pad')
def _pad(dwa: 'DataWithAxes', pad_width, mode = 'constant', **kwargs):
    dwa.create_missing_axes()
    for axis in dwa.axes:
        if not axis.is_axis_linear():
            raise TypeError('Could not pad data with non linear axes')
    if isinstance(pad_width, int):
            pad_width = [(pad_width, pad_width) for _ in range(len(dwa.shape))]
    elif len(pad_width) == 1:
        if hasattr(pad_width[0], '__len__') and len(pad_width[0]) == 2:
            pad_width = [pad_width[0] for _ in range(len(dwa.shape))]
        else:
            pad_width = pad_width[0]
            pad_width = [(pad_width, pad_width) for _ in range(len(dwa.shape))]
    elif len(pad_width) == 2 and not hasattr(pad_width[0], '__len__'):
        pad_width = [pad_width for _ in range(len(dwa.shape))]
    elif len(pad_width) == len(dwa.shape):
        if not hasattr(pad_width[0], '__len__'):
            raise TypeError('Could not pad data with the given argument')
    else:
        raise TypeError(f'Could not pad data with the given arguments: {pad_width}')
    dwa_func = dwa.deepcopy_with_new_data(data=[np.pad(array, pad_width, mode, **kwargs) for array in dwa])
    dwa_func.axes = []
    for axis in deepcopy(dwa.axes):
        axis.offset -= pad_width[axis.index][0] * axis.scaling
        axis.size += pad_width[axis.index][0] + pad_width[axis.index][1]
        dwa_func.axes.append(axis)
    dwa_func.name += f"_{'pad'}"
    return dwa_func


# ******** functions that return booleans ***********
@implements('all')
def _all(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.all, dwa, *args, axis=axis, **kwargs)


@implements('any')
def _any(dwa: 'DataWithAxes', *args, axis: Optional[Union[int, Iterable[int]]] = None, **kwargs):
    return process_with_reduced_dimensions(np.any, dwa, *args, axis=axis, **kwargs)


@implements('allclose')
def _allclose(dwa_a: 'DataWithAxes', dwa_b: 'DataWithAxes', *args,
              **kwargs):
    if dwa_a.size != dwa_b.size or dwa_a.length != dwa_b.length or dwa_a.shape != dwa_b.shape:
        raise ValueError("The two DataWithAxes objects doesn't have arrays of same shape, "
                         "size or length")
    dwa = data_mod.DataCalculated(
        f'allclose_{dwa_a.name}_{dwa_b.name}',
        data=[np.atleast_1d(np.allclose(Q_(dwa_a[ind], dwa_a.units),
                                        Q_(dwa_b[ind], dwa_b.units),
                                        *args, **kwargs)) for ind in range(len(dwa_a))])

    return dwa


# *************** other numpy function ****************

@implements('flipud')
def _flipud(dwa: 'DataWithAxes', *args, **kwargs):
    dwa_func = dwa.deepcopy_with_new_data([np.flipud(data_array) for data_array in dwa])
    return dwa_func


@implements('fliplr')
def _fliplr(dwa: 'DataWithAxes', *args, **kwargs):
    dwa_func = dwa.deepcopy_with_new_data([np.fliplr(data_array) for data_array in dwa])
    return dwa_func


@implements('transpose')
def _transpose(dwa: 'DataWithAxes', *args, **kwargs):
    dwa_func = dwa.deepcopy_with_new_data([np.transpose(data_array) for data_array in dwa])
    return dwa_func


