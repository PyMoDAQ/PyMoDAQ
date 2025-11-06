from typing import TYPE_CHECKING, Callable

from .loss_factory import LossFunctionBase, LossFunctionFactory, LossDim

from adaptive.learner.learner1D import (
    curvature_loss_function,
    default_loss,
    uniform_loss,
    resolution_loss_function,
    abs_min_log_loss,
    uses_nth_neighbors,

)


def default_loss_function(*args, **kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return default_loss


def uniform_loss_function(**kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return uniform_loss


def abs_min_log_loss_function(**kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return abs_min_log_loss



@LossFunctionFactory.register()
class DefaultLoss(LossFunctionBase):
    _loss = staticmethod(default_loss_function)
    dim = LossDim.LOSS_1D
    usual_name = 'Default'
    params = []


@LossFunctionFactory.register()
class UniformLoss(LossFunctionBase):
    _loss = staticmethod(uniform_loss_function)
    dim = LossDim.LOSS_1D
    usual_name = 'Uniform'
    params = []


@LossFunctionFactory.register()
class CurvatureLoss(LossFunctionBase):
    _loss = staticmethod(curvature_loss_function)
    dim = LossDim.LOSS_1D
    usual_name = 'Curvature'
    params = [
        {'title': 'Area', 'name': 'area_factor', 'type': 'float', 'value': 1.},
        {'title': 'Euclid', 'name': 'euclid_factor', 'type': 'float', 'value': 0.02},
        {'title': 'Horizontal', 'name': 'horizontal_factor', 'type': 'float', 'value': 0.02}
    ]


@LossFunctionFactory.register()
class ResolutionLoss(LossFunctionBase):
    _loss = staticmethod(resolution_loss_function)
    dim = LossDim.LOSS_1D
    usual_name = 'Resolution'
    params = [
        {'title': 'Min:', 'name': 'min_length', 'type': 'float', 'value': 0., 'min': 0., 'max': 1.},
        {'title': 'Max:', 'name': 'max_length', 'type': 'float', 'value': 1., 'min': 0., 'max': 1.},
    ]


@LossFunctionFactory.register()
class AbsMinLogLoss(LossFunctionBase):
    _loss = staticmethod(abs_min_log_loss_function)
    dim = LossDim.LOSS_1D
    usual_name = 'AbsMinLog'
    params = []