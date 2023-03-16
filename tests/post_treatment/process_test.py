# -*- coding: utf-8 -*-
"""
Created the 14/02/2023

@author: Sebastien Weber
"""
import numpy as np
import pytest

from pymodaq.utils import data as data_mod
from pymodaq.post_treatment.process_to_scalar import DataProcessorFactory

Nn0 = 11  # navigation axis 0
Nn1 = 7  # navigation axis 1
Nn2 = 4  # navigation axis 2

Nn = [Nn0, Nn1, Nn0]

Ns0 = 10  # signal axis 0
Ns1 = 5  # signal axis 1
Ns = [Ns0, Ns1]

DATA0D = np.random.random((1,))
DATA1D = np.random.random((Ns0,))
DATA2D = np.random.random((Ns0, Ns1))

processors = DataProcessorFactory()


@pytest.fixture()
def init_data_spread():
    Nspread = 21
    sig_axis = data_mod.Axis(label='signal', index=1, data=np.linspace(0, DATA1D.size - 1, DATA1D.size))
    nav_axis_0 = data_mod.Axis(label='nav0', index=0, data=np.random.rand(Nspread), spread_order=0)
    nav_axis_1 = data_mod.Axis(label='nav1', index=0, data=np.random.rand(Nspread), spread_order=1)

    data_array = np.array([ind / Nspread * DATA1D for ind in range(Nspread)])
    data = data_mod.DataRaw('mydata', distribution='spread', data=[data_array], nav_indexes=(0,),
                            axes=[nav_axis_0, sig_axis, nav_axis_1])
    return data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread


def init_data_uniform(Nnav: int = 1, Nsig: int = 1, Ndata: int = 1) -> data_mod.DataWithAxes:
    nav_axes = [data_mod.Axis(label=f'nav{ind}', index=ind, data=np.linspace(0, Nn[ind] - 1, Nn[ind]))
                for ind in range(Nnav)]
    sig_axes = [data_mod.Axis(label=f'sig{ind}', index=ind+len(nav_axes), data=np.linspace(0, Ns[ind] - 1, Ns[ind]))
                for ind in range(Nsig)]

    shape = [n for n in Nn][:Nnav]
    if Nsig == 0:
        shape.append(1)
        data_list = [np.random.random(shape) for _ in range(Ndata)]
    elif Nsig == 1:
        shape.append(Ns0)
        data_list = [np.random.random(shape) for _ in range(Ndata)]
    elif Nsig == 2:
        shape.extend([Ns0, Ns1])
        data_list = [np.random.random(shape) for _ in range(Ndata)]
    data = data_mod.DataRaw('mydata', data=data_list, axes=nav_axes+sig_axes,
                            nav_indexes=[axis.index for axis in nav_axes])
    return data


@pytest.mark.parametrize('dim', ['Data0D', 'Data1D', 'Data2D', 'DataND'])
def test_process_filtered(dim: str):
    dim = data_mod.DataDim[dim]
    functions = processors.functions_filtered(dim)
    for function in functions:
        assert processors.get(function).apply_to >= dim

@pytest.mark.skip
@pytest.mark.parametrize("Ndata", (1, 2, 3))
@pytest.mark.parametrize("Nsig", (1, 2))
@pytest.mark.parametrize("Nnav", (0, 1, 2))
@pytest.mark.parametrize("process", ['min', 'max', 'mean', 'sum', 'std'])
def test_process_multiple_axes_at_once(process, Nnav, Nsig, Ndata):
    """test processors applying to numpy functions that can be applied on specific axes, here the signal axes"""
    if process in processors.functions:
        data = init_data_uniform(Nnav=Nnav, Nsig=Nsig, Ndata=Ndata)
        data_processed = processors.get(process).process(data)
        for ind in range(len(data)):
            assert getattr(np, process)(data[ind], axis=data.sig_indexes) == pytest.approx(data_processed[ind])

        if Nnav == 0:
            assert data_processed.dim == 'Data0D'
        if Nnav == 1:
            assert data_processed.dim == 'Data1D'
        if Nnav == 2:
            assert data_processed.dim == 'Data2D'
        assert data_processed.distribution == 'uniform'
        assert data_processed.source == 'calculated'










