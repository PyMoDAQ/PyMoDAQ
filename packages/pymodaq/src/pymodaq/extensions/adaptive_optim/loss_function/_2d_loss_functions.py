from typing import TYPE_CHECKING, Callable

from .loss_factory import LossFunctionBase, LossFunctionFactory, LossDim

from adaptive.learner.learner2D import (
    default_loss,
    uniform_loss,
    resolution_loss_function,
    minimize_triangle_surface_loss,
    thresholded_loss_function,
)


def default_loss_function(*args, **kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return default_loss


def uniform_loss_function(**kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return uniform_loss


def minimize_triangle_surface_loss_function(**kwargs):  #should be wrapped to handle eventual initializing argument, see params attributes below
    return minimize_triangle_surface_loss


@LossFunctionFactory.register()
class DefaultLoss(LossFunctionBase):
    _loss = staticmethod(default_loss_function)
    dim = LossDim.LOSS_2D
    usual_name = 'Default'
    params = []


@LossFunctionFactory.register()
class UniformLoss(LossFunctionBase):
    _loss = staticmethod(uniform_loss_function)
    dim = LossDim.LOSS_2D
    usual_name = 'Uniform'
    params = []



@LossFunctionFactory.register()
class ResolutionLoss(LossFunctionBase):
    _loss = staticmethod(resolution_loss_function)
    dim = LossDim.LOSS_2D
    usual_name = 'Resolution'
    params = [
        {'title': 'Min:', 'name': 'min_distance', 'type': 'float', 'value': 0., 'min': 0., 'max': 1.},
        {'title': 'Max:', 'name': 'max_distance', 'type': 'float', 'value': 1., 'min': 0., 'max': 1.},
    ]


@LossFunctionFactory.register()
class MinTriangleLoss(LossFunctionBase):
    _loss = staticmethod(minimize_triangle_surface_loss_function)
    dim = LossDim.LOSS_2D
    usual_name = 'MinTriangle'
    params = []



@LossFunctionFactory.register()
class ThresholdLoss(LossFunctionBase):
    _loss = staticmethod(thresholded_loss_function)
    dim = LossDim.LOSS_2D
    usual_name = 'Threshold'
    params = [
        {'title': 'Lower:', 'name': 'lower_threshold', 'type': 'float', 'value': None,},
        {'title': 'Upper:', 'name': 'upper_threshold', 'type': 'float', 'value': None,},
        {'title': 'Priority factor:', 'name': 'priority_factor', 'type': 'float', 'value': 0.1,},
    ]

