from .loss_factory import LossFunctionBase, LossFunctionFactory, LossDim


LossFunctionFactory.register()
from adaptive.learner.learner1D import (
    curvature_loss_function,
    default_loss,
    uniform_loss,
)


LossFunctionFactory.register()
class DefaultLoss(LossFunctionBase):
    _loss = default_loss
    dim = LossDim.LOSS_1D
    usual_name = 'Default'
    params = []


LossFunctionFactory.register()
class UniformLoss(LossFunctionBase):
    _loss = uniform_loss
    dim = LossDim.LOSS_1D
    usual_name = 'Uniform'
    params = []


LossFunctionFactory.register()
class CurvatureLoss(LossFunctionBase):
    _loss = curvature_loss_function
    dim = LossDim.LOSS_1D
    usual_name = 'Curvature'
    params = []