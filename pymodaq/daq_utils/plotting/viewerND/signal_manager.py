# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 16:41:26 2018

@author: Weber Sébastien
@email: seba.weber@gmail.com
"""
import numpy as np
import collections
import copy

import math
from pymodaq.daq_utils import daq_utils as utils


# %%
def generate_axis(offset, scale, size, offset_index=0):
    """Creates an axis given the offset, scale and number of channels

    Alternatively, the offset_index of the offset channel can be specified.

    Parameters
    ----------
    offset : float
    scale : float
    size : number of channels
    offset_index : int
        offset_index number of the offset

    Returns
    -------
    Numpy array

    """
    return np.linspace(offset - offset_index * scale,
                       offset + scale * (size - 1 - offset_index),
                       size)


def add_scalar_axis(signal):
    am = signal.axes_manager
    signal.__class__ = Signal
    am.remove(am._axes)
    am._append_axis(size=1,
                    scale=1,
                    offset=0,
                    name="Scalar",
                    navigate=False)


def isfloat(number):
    """Check if a number or array is of float type.

    This is necessary because e.g. isinstance(np.float32(2), float) is False.

    """
    if hasattr(number, "dtype"):
        return np.issubdtype(number, np.float)
    else:
        return isinstance(number, float)


def iterable_not_string(thing):
    return isinstance(thing, collections.Iterable) and not isinstance(thing, str)


class SpecialSlicers(object):

    def __init__(self, obj, isNavigation):
        self.isNavigation = isNavigation
        self.obj = obj

    def __getitem__(self, slices, out=None):
        return self.obj._slicer(slices, self.isNavigation, out=out)


class SpecialSlicersSignal(SpecialSlicers):

    def __setitem__(self, i, j):
        """x.__setitem__(i, y) <==> x[i]=y
        """
        if isinstance(j, Signal):
            j = j.data
        array_slices = self.obj._get_array_slices(i, self.isNavigation)
        self.obj.data[array_slices] = j

    def __len__(self):
        return self.obj.axes_manager.signal_shape[0]


class attrgetter:
    """
    Return a callable object that fetches the given attribute(s) from its operand.
    After f = attrgetter('name'), the call f(r) returns r.name.
    After g = attrgetter('name', 'date'), the call g(r) returns (r.name, r.date).
    After h = attrgetter('name.first', 'name.last'), the call h(r) returns
    (r.name.first, r.name.last).
    """
    __slots__ = ('_attrs', '_call')

    def __init__(self, attr, *attrs):
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError('attribute name must be a string')
            self._attrs = (attr,)
            names = attr.split('.')

            def func(obj):
                for name in names:
                    obj = getattr(obj, name)
                return obj
            self._call = func
        else:
            self._attrs = (attr,) + attrs
            getters = tuple(map(attrgetter, self._attrs))

            def func(obj):
                return tuple(getter(obj) for getter in getters)
            self._call = func

    def __call__(self, obj):
        return self._call(obj)

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__qualname__,
                              ', '.join(map(repr, self._attrs)))

    def __reduce__(self):
        return self.__class__, self._attrs


def attrsetter(target, attrs, value):
    """ Sets attribute of the target to specified value, supports nested
        attributes. Only creates a new attribute if the object supports such
        behaviour (e.g. DictionaryTreeBrowser does)

        Parameters
        ----------
            target : object
            attrs : string
                attributes, separated by periods (e.g.
                'metadata.Signal.Noise_parameters.variance' )
            value : object

        Example
        -------
        First create a signal and model pair:

        >>> s = hs.signals.Signal1D(np.arange(10))
        >>> m = s.create_model()
        >>> m.signal.data
        array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        Now set the data of the model with attrsetter
        >>> attrsetter(m, 'signal1D.data', np.arange(10)+2)
        >>> self.signal.data
        array([2, 3, 4, 5, 6, 7, 8, 9, 10, 10])

        The behaviour is identical to
        >>> self.signal.data = np.arange(10) + 2


    """
    where = attrs.rfind('.')
    if where != -1:
        target = attrgetter(attrs[:where])(target)
    setattr(target, attrs[where + 1:], value)


class FancySlicing(object):

    def _get_array_slices(self, slices, isNavigation=None):
        try:
            len(slices)
        except TypeError:
            slices = (slices,)

        slices_ = tuple()
        for sl in slices:
            slices_ += (sl,)
        slices = slices_
        del slices_
        _orig_slices = slices

        has_nav = True if isNavigation is None else isNavigation
        has_signal = True if isNavigation is None else not isNavigation

        # Create a deepcopy of self that contains a view of self.data

        nav_idx = [el.index_in_array for el in
                   self.axes_manager.navigation_axes]
        signal_idx = [el.index_in_array for el in
                      self.axes_manager.signal_axes]

        if not has_signal:
            idx = nav_idx
        elif not has_nav:
            idx = signal_idx
        else:
            idx = nav_idx + signal_idx

        # Add support for Ellipsis
        if Ellipsis in _orig_slices:
            _orig_slices = list(_orig_slices)
            # Expand the first Ellipsis
            ellipsis_index = _orig_slices.index(Ellipsis)
            _orig_slices.remove(Ellipsis)
            _orig_slices = (_orig_slices[:ellipsis_index] + [slice(None), ] * max(0, len(idx) - len(
                _orig_slices)) + _orig_slices[ellipsis_index:])
            # Replace all the following Ellipses by :
            while Ellipsis in _orig_slices:
                _orig_slices[_orig_slices.index(Ellipsis)] = slice(None)
            _orig_slices = tuple(_orig_slices)

        if len(_orig_slices) > len(idx):
            raise IndexError("too many indices")

        slices = np.array([slice(None, )] * len(self.axes_manager._axes))

        slices[idx] = _orig_slices + (slice(None),) * max(
            0, len(idx) - len(_orig_slices))

        array_slices = []
        for slice_, axis in zip(slices, self.axes_manager._axes):
            if (isinstance(slice_, slice) or len(self.axes_manager._axes) < 2):
                array_slices.append(axis._get_array_slices(slice_))
            else:
                if isinstance(slice_, float):
                    slice_ = axis.value2index(slice_)
                array_slices.append(slice_)
        return tuple(array_slices)

    def _slicer(self, slices, isNavigation=None, out=None):
        array_slices = self._get_array_slices(slices, isNavigation)
        new_data = self.data[array_slices]
        if new_data.size == 1 and new_data.dtype is np.dtype('O'):
            if isinstance(new_data[0], np.ndarray):
                return self.__class__(new_data[0]).transpose(navigation_axes=0)
            else:
                return new_data[0]

        if out is None:
            _obj = self._deepcopy_with_new_data(new_data,
                                                copy_variance=True)
            _to_remove = []
            for slice_, axis in zip(array_slices, _obj.axes_manager._axes):
                if (isinstance(slice_, slice) or len(self.axes_manager._axes) < 2):
                    axis._slice_me(slice_)
                else:
                    _to_remove.append(axis.index_in_axes_manager)
            for _ind in reversed(sorted(_to_remove)):
                _obj._remove_axis(_ind)
        else:
            out.data = new_data
            _obj = out
            i = 0
            for slice_, axis_src in zip(array_slices, self.axes_manager._axes):
                axis_src = axis_src.copy()
                if (isinstance(slice_, slice) or len(self.axes_manager._axes) < 2):
                    axis_src._slice_me(slice_)
                    axis_dst = out.axes_manager._axes[i]
                    i += 1
                    axis_dst.update_from(axis_src, attributes=("scale", "offset", "size"))

        if hasattr(self, "_additional_slicing_targets"):
            for ta in self._additional_slicing_targets:
                try:
                    t = attrgetter(ta)(self)
                    if out is None:
                        if hasattr(t, '_slicer'):
                            attrsetter(
                                _obj,
                                ta,
                                t._slicer(
                                    slices,
                                    isNavigation))
                    else:
                        target = attrgetter(ta)(_obj)
                        t._slicer(
                            slices,
                            isNavigation,
                            out=target)

                except AttributeError:
                    pass
        # _obj.get_dimensions_from_data() # replots, so we do it manually:
        dc = _obj.data
        for axis in _obj.axes_manager._axes:
            axis.size = int(dc.shape[axis.index_in_array])
        if out is None:
            return _obj
        else:
            out.events.data_changed.trigger(obj=out)


class DataAxis(object):

    def __init__(self,
                 size,
                 index_in_array=None,
                 name=None,
                 scale=1.,
                 offset=0.,
                 units=None,
                 navigate=None):

        self.name = name
        self.units = units
        self.scale = scale
        self.offset = offset
        self.size = size
        self.value = None
        self.high_index = self.size - 1
        self.low_index = 0
        self.index = 0
        self.update_axis()
        self.navigate = navigate
        self.axes_manager = None
        self._update_slice(self.navigate)

    def _index_changed(self, name, old, new):
        self.events.index_changed.trigger(obj=self, index=self.index)
        if not self._suppress_update_value:
            new_value = self.axis[self.index]
            if new_value != self.value:
                self.value = new_value

    @property
    def index_in_array(self):
        if self.axes_manager is not None:
            return self.axes_manager._axes.index(self)
        else:
            raise AttributeError(
                "This DataAxis does not belong to an AxesManager"
                " and therefore its index_in_array attribute "
                " is not defined")

    @property
    def index_in_axes_manager(self):
        if self.axes_manager is not None:
            return self.axes_manager._get_axes_in_natural_order(). \
                index(self)
        else:
            raise AttributeError(
                "This DataAxis does not belong to an AxesManager"
                " and therefore its index_in_array attribute "
                " is not defined")

    def _get_positive_index(self, index):
        if index < 0:
            index = self.size + index
            if index < 0:
                raise IndexError("index out of bounds")
        return index

    def _get_index(self, value):
        if isfloat(value):
            return self.value2index(value)
        else:
            return value

    def _slice_me(self, slice_):
        """Returns a slice to slice the corresponding data axis and
        change the offset and scale of the DataAxis accordingly.

        Parameters
        ----------
        slice_ : {float, int, slice}

        Returns
        -------
        my_slice : slice

        """
        i2v = self.index2value

        my_slice = self._get_array_slices(slice_)

        start, stop, step = my_slice.start, my_slice.stop, my_slice.step

        if start is None:
            if step is None or step > 0:
                start = 0
            else:
                start = self.size - 1
        self.offset = i2v(start)
        if step is not None:
            self.scale *= step

        return my_slice

    @property
    def index_in_array(self):
        if self.axes_manager is not None:
            return self.axes_manager._axes.index(self)
        else:
            raise AttributeError(
                "This DataAxis does not belong to an AxesManager"
                " and therefore its index_in_array attribute "
                " is not defined")

    def value2index(self, value, rounding=round):
        """Return the closest index to the given value if between the limit.

        Parameters
        ----------
        value : number or numpy array

        Returns
        -------
        index : integer or numpy array

        Raises
        ------
        ValueError if any value is out of the axis limits.

        """
        if value is None:
            return None

        if isinstance(value, np.ndarray):
            if rounding is round:
                rounding = np.round
            elif rounding is math.ceil:
                rounding = np.ceil
            elif rounding is math.floor:
                rounding = np.floor

        index = rounding((value - self.offset) / self.scale)

        if isinstance(value, np.ndarray):
            index = index.astype(int)
            if np.all(self.size > index) and np.all(index >= 0):
                return index
            else:
                raise ValueError("A value is out of the axis limits")
        else:
            index = int(index)
            if self.size > index >= 0:
                return index
            else:
                raise ValueError("The value is out of the axis limits")

    def index2value(self, index):
        if isinstance(index, np.ndarray):
            return self.axis[index.ravel()].reshape(index.shape)
        else:
            return self.axis[index]

    def _get_array_slices(self, slice_):
        """Returns a slice to slice the corresponding data axis without
        changing the offset and scale of the DataAxis.

        Parameters
        ----------
        slice_ : {float, int, slice}

        Returns
        -------
        my_slice : slice

        """
        v2i = self.value2index

        if isinstance(slice_, slice):
            start = slice_.start
            stop = slice_.stop
            step = slice_.step
        else:
            if isfloat(slice_):
                start = v2i(slice_)
            else:
                start = self._get_positive_index(slice_)
            stop = start + 1
            step = None

        if isfloat(step):
            step = int(round(step / self.scale))
        if isfloat(start):
            try:
                start = v2i(start)
            except ValueError:
                if start > self.high_value:
                    # The start value is above the axis limit
                    raise IndexError(
                        "Start value above axis high bound for  axis %s."
                        "value: %f high_bound: %f" % (repr(self), start,
                                                      self.high_value))
                else:
                    # The start value is below the axis limit,
                    # we slice from the start.
                    start = None
        if isfloat(stop):
            try:
                stop = v2i(stop)
            except ValueError:
                if stop < self.low_value:
                    # The stop value is below the axis limits
                    raise IndexError(
                        "Stop value below axis low bound for  axis %s."
                        "value: %f low_bound: %f" % (repr(self), stop,
                                                     self.low_value))
                else:
                    # The stop value is below the axis limit,
                    # we slice until the end.
                    stop = None

        if step == 0:
            raise ValueError("slice step cannot be zero")

        return slice(start, stop, step)

    def update_axis(self):
        self.axis = generate_axis(self.offset, self.scale, self.size)
        if len(self.axis) != 0:
            self.low_value, self.high_value = (
                self.axis.min(), self.axis.max())
        self.value = [self.low_value, self.high_value]

    def _update_slice(self, value):
        if value is False:
            self.slice = slice(None)
        else:
            self.slice = None

    @property
    def index_in_axes_manager(self):
        if self.axes_manager is not None:
            return self.axes_manager._get_axes_in_natural_order(). \
                index(self)
        else:
            raise AttributeError(
                "This DataAxis does not belong to an AxesManager"
                " and therefore its index_in_array attribute "
                " is not defined")


class AxesManager(object):

    def __init__(self, axes_list):
        self._axes = []
        self.create_axes(axes_list)
        # set_signal_dimension is called only if there is no current
        # view. It defaults to spectrum
        navigates = [i.navigate for i in self._axes]
        self._update_attributes()

    def _append_axis(self, *args, **kwargs):
        axis = DataAxis(*args, **kwargs)
        axis.axes_manager = self
        self._axes.append(axis)

    def remove(self, axes):
        """Remove one or more axes
        """
        axes = self[axes]
        if not np.iterable(axes):
            axes = (axes,)
        for ax in axes:
            self._remove_one_axis(ax)

    def _remove_one_axis(self, axis):
        """Remove the given Axis.

        Raises
        ------
        ValueError if the Axis is not present.

        """
        axis = self._axes_getter(axis)
        axis.axes_manager = None
        self._axes.remove(axis)

    def __getitem__(self, y):
        """x.__getitem__(y) <==> x[y]

        """
        if isinstance(y, str) or not np.iterable(y):
            return self[(y,)][0]
        axes = [self._axes_getter(ax) for ax in y]
        _, indices = np.unique(
            [_id for _id in map(id, axes)], return_index=True)
        ans = tuple(axes[i] for i in sorted(indices))
        return ans

    def _axes_getter(self, y):
        if y in self._axes:
            return y
        if isinstance(y, str):
            axes = list(self._get_axes_in_natural_order())
            while axes:
                axis = axes.pop()
                if y == axis.name:
                    return axis
            raise ValueError("There is no DataAxis named %s" % y)
        elif (isfloat(y.real) and not y.real.is_integer() or isfloat(y.imag) and not y.imag.is_integer()):
            raise TypeError("axesmanager indices must be integers, "
                            "complex integers or strings")
        if y.imag == 0:  # Natural order
            return self._get_axes_in_natural_order()[y]
        elif y.imag == 3:  # Array order
            # Array order
            return self._axes[int(y.real)]
        elif y.imag == 1:  # Navigation natural order
            #
            return self.navigation_axes[int(y.real)]
        elif y.imag == 2:  # Signal natural order
            return self.signal_axes[int(y.real)]
        else:
            raise IndexError("axesmanager imaginary part of complex indices "
                             "must be 0, 1, 2 or 3")

    def __getslice__(self, i=None, j=None):
        """x.__getslice__(i, j) <==> x[i:j]

        """
        return self._get_axes_in_natural_order()[i:j]

    def create_axes(self, axes_list):
        """Given a list of dictionaries defining the axes properties
        create the DataAxis instances and add them to the AxesManager.

        The index of the axis in the array and in the `_axes` lists
        can be defined by the index_in_array keyword if given
        for all axes. Otherwise it is defined by their index in the
        list.

        See also
        --------
        _append_axis

        """
        for axis_dict in axes_list:
            self._append_axis(**axis_dict)

    def _get_axes_in_natural_order(self):
        return self.navigation_axes + self.signal_axes

    def _update_attributes(self):
        getitem_tuple = []
        values = []
        self.signal_axes = ()
        self.navigation_axes = ()
        for axis in self._axes:
            # Until we find a better place, take property of the axes
            # here to avoid difficult to debug bugs.
            axis.axes_manager = self
            if axis.slice is None:
                getitem_tuple += axis.index,
                values.append(axis.value)
                self.navigation_axes += axis,
            else:
                getitem_tuple += axis.slice,
                self.signal_axes += axis,
        if not self.signal_axes and self.navigation_axes:
            getitem_tuple[-1] = slice(axis.index, axis.index + 1)

        self.signal_axes = self.signal_axes[::-1]
        self.navigation_axes = self.navigation_axes[::-1]
        self._getitem_tuple = tuple(getitem_tuple)
        self.signal_dimension = len(self.signal_axes)
        self.navigation_dimension = len(self.navigation_axes)
        if self.navigation_dimension != 0:
            self.navigation_shape = tuple([
                axis.size for axis in self.navigation_axes])
        else:
            self.navigation_shape = ()

        if self.signal_dimension != 0:
            self.signal_shape = tuple([
                axis.size for axis in self.signal_axes])
        else:
            self.signal_shape = ()
        self.navigation_size = (np.cumprod(self.navigation_shape)[-1]
                                if self.navigation_shape else 0)
        self.signal_size = (np.cumprod(self.signal_shape)[-1]
                            if self.signal_shape else 0)
        self._update_max_index()

    def _update_max_index(self):
        self._max_index = 1
        for i in self.navigation_shape:
            self._max_index *= i
        if self._max_index != 0:
            self._max_index -= 1

    @property
    def shape(self):
        nav_shape = (self.navigation_shape
                     if self.navigation_shape != (0,)
                     else tuple())
        sig_shape = (self.signal_shape
                     if self.signal_shape != (0,)
                     else tuple())
        return nav_shape + sig_shape

    def _get_dimension_str(self):
        string = "("
        for axis in self.navigation_axes:
            string += str(axis.size) + ", "
        string = string.rstrip(", ")
        string += "|"
        for axis in self.signal_axes:
            string += str(axis.size) + ", "
        string = string.rstrip(", ")
        string += ")"
        return string

    def __repr__(self):
        text = ('<Axes manager, axes: %s>\n' %
                self._get_dimension_str())
        ax_signature = "% 16s | %6g | %6s | %7.2g | %7.2g | %6s "
        signature = "% 16s | %6s | %6s | %7s | %7s | %6s "
        text += signature % ('Name', 'size', 'index', 'offset', 'scale',
                             'units')
        text += '\n'
        text += signature % ('=' * 16, '=' * 6, '=' * 6,
                             '=' * 7, '=' * 7, '=' * 6)
        for ax in self.navigation_axes:
            text += '\n'
            text += ax_signature % (str(ax.name)[:16], ax.size, str(ax.index),
                                    ax.offset, ax.scale, ax.units)
        text += '\n'
        text += signature % ('-' * 16, '-' * 6, '-' * 6,
                             '-' * 7, '-' * 7, '-' * 6)
        for ax in self.signal_axes:
            text += '\n'
            text += ax_signature % (str(ax.name)[:16], ax.size, ' ', ax.offset,
                                    ax.scale, ax.units)

        return text

    def _update_axes(self, old_axes, navigation_axes, signal_axes):

        for ind_ax, ax in enumerate(self._axes):
            navigate = old_axes[ind_ax] in navigation_axes
            ax.navigate = navigate
            ax._update_slice(navigate)


class Signal(FancySlicing):

    def __init__(self, data, **kwds):
        """Create a Signal from a numpy array.

        Parameters
        ----------
        data : numpy array
           The signal data. It can be an array of any dimensions.
        axes : dictionary (optional)
            Dictionary to define the axes (see the
            documentation of the AxesManager class for more details).
        """
        self.data = data

        if 'axes' not in kwds:
            kwds['axes'] = self._get_undefined_axes_list()
        self.axes_manager = AxesManager(kwds['axes'])

        self.inav = SpecialSlicersSignal(self, True)
        self.isig = SpecialSlicersSignal(self, False)

    def _remove_axis(self, axes):
        am = self.axes_manager
        axes = am[axes]
        if not np.iterable(axes):
            axes = (axes,)
        if am.navigation_dimension + am.signal_dimension > len(axes):
            old_signal_dimension = am.signal_dimension
            am.remove(axes)
            if old_signal_dimension != am.signal_dimension:
                self._assign_subclass()
        else:
            # Create a "Scalar" axis because the axis is the last one left and
            add_scalar_axis(self)

    def _get_undefined_axes_list(self):
        axes = []
        for s in self.data.shape:
            axes.append({'size': int(s), })
        return axes

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = np.atleast_1d(np.asanyarray(value))

    def __repr__(self):
        unfolded = ""
        string = '<'
        string += self.__class__.__name__
        string += ", %sdimensions: %s" % (
            unfolded,
            self.axes_manager._get_dimension_str())

        string += '>'

        return string

    def _apply_function_on_data_and_remove_axis(self, function, axes,
                                                out=None):
        axes = self.axes_manager[axes]
        if not np.iterable(axes):
            axes = (axes,)
        # Use out argument in numpy function when available for operations that
        # do not return scalars in numpy.
        np_out = not len(self.axes_manager._axes) == len(axes)
        ar_axes = tuple(ax.index_in_array for ax in axes)
        if len(ar_axes) == 1:
            ar_axes = ar_axes[0]

        s = out or self._deepcopy_with_new_data(None)

        if np.ma.is_masked(self.data):
            return self._ma_workaround(s=s, function=function, axes=axes,
                                       ar_axes=ar_axes, out=out)
        if out:
            if np_out:
                function(self.data, axis=ar_axes, out=out.data, )
            else:
                data = np.atleast_1d(function(self.data, axis=ar_axes, ))
                if data.shape == out.data.shape:
                    out.data[:] = data
                else:
                    raise ValueError(
                        "The output shape %s does not match  the shape of "
                        "`out` %s" % (data.shape, out.data.shape))
            out.events.data_changed.trigger(obj=out)
        else:
            s.data = np.atleast_1d(
                function(self.data, axis=ar_axes, ))
            s._remove_axis([ax.index_in_axes_manager for ax in axes])
            return s

    def sum(self, axis=None, out=None):
        """Sum the data over the given axes.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        max, min, mean, std, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.sum(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.sum, axis,
                                                            out=out)

    def halflife(self, axis=None, out=None):
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(self._halflife_fun, axis,
                                                            out=out)

    def _halflife_fun(self, sub_data, axis=None):
        try:

            indexes = [s for s in range(len(sub_data.shape)) if s not in [axis]]
            out_shape = tuple(np.array((sub_data.shape))[indexes])
            time = np.zeros((np.prod(out_shape)))
            data_reshaped = sub_data.reshape((np.prod(out_shape), sub_data.shape[axis]))
            for ind_dat in range(np.prod(out_shape)):
                dat = data_reshaped[ind_dat, :]
                ind_x0 = utils.find_index(dat, np.max(dat))[0][0]
                sub_xaxis = np.linspace(0, len(dat), len(dat), endpoint=False)
                x0 = sub_xaxis[ind_x0]
                sub_xaxis = sub_xaxis[ind_x0:]

                dat_clipped = dat[ind_x0:]
                offset = dat_clipped[-1]
                N0 = np.max(dat_clipped) - offset
                thalf = sub_xaxis[utils.find_index(dat - offset, 0.5 * N0)[0][0]] - x0
                time[ind_dat] = thalf
            return time.reshape(out_shape)
        except Exception as e:
            return time.reshape(out_shape)

    def max(self, axis=None, out=None):
        """Returns a signal with the maximum of the signal along at least one
        axis.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        min, sum, mean, std, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.max(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.max, axis,
                                                            out=out)

    def min(self, axis=None, out=None):
        """Returns a signal with the minimum of the signal along at least one
        axis.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        max, sum, mean, std, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.min(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.min, axis,
                                                            out=out)

    def mean(self, axis=None, out=None):
        """Returns a signal with the average of the signal along at least one
        axis.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        max, min, sum, std, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.mean(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.mean, axis,
                                                            out=out)

    def std(self, axis=None, out=None):
        """Returns a signal with the standard deviation of the signal along
        at least one axis.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        max, min, sum, mean, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.std(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.std, axis,
                                                            out=out)

    def var(self, axis=None, out=None):
        """Returns a signal with the variances of the signal along at least one
        axis.

        Parameters
        ----------
        axis %s
        %s

        Returns
        -------
        s : Signal

        See also
        --------
        max, min, sum, mean, std, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.var(-1).data.shape
        (64,64)

        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.var, axis,
                                                            out=out)

    def nansum(self, axis=None, out=None):
        """%s
        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nansum, axis,
                                                            out=out)

    def nanmax(self, axis=None, out=None):
        """%s
        """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nanmax, axis,
                                                            out=out)

    def nanmin(self, axis=None, out=None):
        """%s"""
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nanmin, axis,
                                                            out=out)

    def nanmean(self, axis=None, out=None):
        """%s """
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nanmean, axis,
                                                            out=out)

    def nanstd(self, axis=None, out=None):
        """%s"""
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nanstd, axis,
                                                            out=out)

    def nanvar(self, axis=None, out=None):
        """%s"""
        if axis is None:
            axis = self.axes_manager.navigation_axes
        return self._apply_function_on_data_and_remove_axis(np.nanvar, axis,
                                                            out=out)

    def diff(self, axis, order=1, out=None):
        """Returns a signal with the n-th order discrete difference along
        given axis.

        Parameters
        ----------
        axis %s
        order : int
            the order of the derivative
        %s

        See also
        --------
        max, min, sum, mean, std, var, indexmax, valuemax, amax

        Examples
        --------
        >>> import numpy as np
        >>> s = BaseSignal(np.random.random((64,64,1024)))
        >>> s.data.shape
        (64,64,1024)
        >>> s.diff(-1).data.shape
        (64,64,1023)
        """
        s = out or self._deepcopy_with_new_data(None)
        data = np.diff(self.data, n=order,
                       axis=self.axes_manager[axis].index_in_array)
        if out is not None:
            out.data[:] = data
        else:
            s.data = data
        axis2 = s.axes_manager[axis]
        new_offset = self.axes_manager[axis].offset + (order * axis2.scale / 2)
        axis2.offset = new_offset
        s.get_dimensions_from_data()
        if out is None:
            return s
        else:
            out.events.data_changed.trigger(obj=out)

    def transpose(self, signal_axes=None,
                  navigation_axes=None, optimize=False):
        """Transposes the signal to have the required signal and navigation
        axes.

        Parameters
        ----------
        signal_axes, navigation_axes : {None, int, iterable}
            With the exception of both parameters getting iterables, generally
            one has to be None (i.e. "floating"). The other one specifies
            either the required number or explicitly the axes to move to the
            corresponding space.
            If both are iterables, full control is given as long as all axes
            are assigned to one space only.
        optimize : bool [False]
            If the data should be re-ordered in memory, most likely making a
            copy. Ensures the fastest available iteration at the expense of
            memory.

        See also
        --------
        T, as_signal2D, as_signal1D, hs.transpose

        Examples
        --------
        >>> # just create a signal with many distinct dimensions
        >>> s = hs.signals.Signal(np.random.rand(1,2,3,4,5,6,7,8,9))
        >>> s
        <Signal, title: , dimensions: (|9, 8, 7, 6, 5, 4, 3, 2, 1)>

        >>> s.transpose() # swap signal and navigation spaces
        <Signal, title: , dimensions: (9, 8, 7, 6, 5, 4, 3, 2, 1|)>

        >>> s.T # a shortcut for no arguments
        <Signal, title: , dimensions: (9, 8, 7, 6, 5, 4, 3, 2, 1|)>

        # roll to leave 5 axes in navigation space
        >>> s.transpose(signal_axes=5)
        <Signal, title: , dimensions: (4, 3, 2, 1|9, 8, 7, 6, 5)>

        # roll leave 3 axes in navigation space
        >>> s.transpose(navigation_axes=3)
        <Signal, title: , dimensions: (3, 2, 1|9, 8, 7, 6, 5, 4)>

        >>> # 3 explicitly defined axes in signal space
        >>> s.transpose(signal_axes=[0, 2, 6])
        <Signal, title: , dimensions: (8, 6, 5, 4, 2, 1|9, 7, 3)>

        >>> # A mix of two lists, but specifying all axes explicitly
        >>> # The order of axes is preserved in both lists
        >>> s.transpose(navigation_axes=[1, 2, 3, 4, 5, 8], signal_axes=[0, 6, 7])
        <Signal, title: , dimensions: (8, 7, 6, 5, 4, 1|9, 3, 2)>

        """

        am = self.axes_manager
        ns = self.axes_manager.navigation_axes + self.axes_manager.signal_axes
        ax_list = am._axes
        if isinstance(signal_axes, int):
            if navigation_axes is not None:
                raise ValueError("The navigation_axes are not None, even "
                                 "though just a number was given for "
                                 "signal_axes")
            if len(ax_list) < signal_axes:
                raise ValueError("Too many signal axes requested")
            if signal_axes < 0:
                raise ValueError("Can't have negative number of signal axes")
            elif signal_axes == 0:
                signal_axes = ()
                navigation_axes = ax_list[::-1]
            else:
                navigation_axes = ax_list[:-signal_axes][::-1]
                signal_axes = ax_list[-signal_axes:][::-1]
        elif iterable_not_string(signal_axes):
            signal_axes = tuple(am[ax] for ax in signal_axes)
            if navigation_axes is None:
                navigation_axes = tuple(ax for ax in ax_list
                                        if ax not in signal_axes)[::-1]
            elif iterable_not_string(navigation_axes):
                # want to keep the order
                navigation_axes = tuple(am[ax] for ax in navigation_axes)
                intersection = set(signal_axes).intersection(navigation_axes)
                if len(intersection):
                    raise ValueError("At least one axis found in both spaces:"
                                     " {}".format(intersection))
                if len(am._axes) != (len(signal_axes) + len(navigation_axes)):
                    raise ValueError("Not all current axes were assigned to a "
                                     "space")
            else:
                raise ValueError("navigation_axes has to be None or an iterable"
                                 " when signal_axes is iterable")
        elif signal_axes is None:
            if isinstance(navigation_axes, int):
                if len(ax_list) < navigation_axes:
                    raise ValueError("Too many navigation axes requested")
                if navigation_axes < 0:
                    raise ValueError(
                        "Can't have negative number of navigation axes")
                elif navigation_axes == 0:
                    navigation_axes = ()
                    signal_axes = ax_list[::-1]
                else:
                    signal_axes = ax_list[navigation_axes:][::-1]
                    navigation_axes = ax_list[:navigation_axes][::-1]
            elif iterable_not_string(navigation_axes):
                navigation_axes = tuple(am[ax] for ax in
                                        navigation_axes)
                signal_axes = tuple(ax for ax in ax_list
                                    if ax not in navigation_axes)[::-1]
            elif navigation_axes is None:
                signal_axes = am.navigation_axes
                navigation_axes = am.signal_axes
            else:
                raise ValueError(
                    "The passed navigation_axes argument is not valid")
        else:
            raise ValueError("The passed signal_axes argument is not valid")
        # translate to axes idx from actual objects for variance
        idx_sig = [ax.index_in_axes_manager for ax in signal_axes]
        idx_nav = [ax.index_in_axes_manager for ax in navigation_axes]
        # From now on we operate with axes in array order
        signal_axes = signal_axes[::-1]
        navigation_axes = navigation_axes[::-1]
        # get data view
        array_order = tuple(
            ax.index_in_array for ax in navigation_axes)
        array_order += tuple(ax.index_in_array for ax in signal_axes)
        newdata = self.data.transpose(array_order)
        res = self._deepcopy_with_new_data(newdata, copy_variance=True)

        # reconfigure the axes of the axesmanager:
        ram = res.axes_manager
        # ram._update_trait_handlers(remove=True)
        ram._update_axes(self.axes_manager._axes, navigation_axes, signal_axes)

        # _axes are ordered in array order
        ram._axes = [ram._axes[i] for i in array_order]
        for i, ax in enumerate(ram._axes):
            if i < len(navigation_axes):
                ax.navigate = True
            else:
                ax.navigate = False
        ram._update_attributes()

        return res

    @property
    def T(self):
        """The transpose of the signal, with signal and navigation spaces
        swapped.
        """
        return self.transpose()

    def _deepcopy_with_new_data(self, data=None, copy_variance=False):
        """Returns a deepcopy of itself replacing the data.

        This method has the advantage over deepcopy that it does not
        copy the data what can save precious memory

        Parameters
        ---------
        data : {None | np.array}

        Returns
        -------
        ns : Signal

        """
        old_np = None
        try:
            old_data = self.data
            self.data = None
            ns = self.deepcopy()
            ns.data = data
            return ns
        finally:
            self.data = old_data

    def deepcopy(self):
        return copy.deepcopy(self)


if __name__ == '__main__':
    # import hyperspy.api as hs

    data = np.array([[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]])

    # signal_hs=hs.signals.BaseSignal(data)
    # print(signal_hs)
    # signal_hs_t=signal_hs.transpose(signal_axes=[1])
    # print(signal_hs_t)

    signal = Signal(data)
    print(signal)

    signal_t = signal.transpose(signal_axes=[1])
    print(signal_t)
