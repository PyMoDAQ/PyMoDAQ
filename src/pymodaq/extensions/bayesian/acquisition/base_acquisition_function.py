from bayes_opt.acquisition import UpperConfidenceBound, ExpectedImprovement, ProbabilityOfImprovement
from pymodaq.extensions.bayesian.acquisition import GenericAcquisitionFunctionFactory, GenericAcquisitionFunctionBase


@GenericAcquisitionFunctionFactory.register()
class GenericUpperConfidenceBound(GenericAcquisitionFunctionBase):
    usual_name = "Upper Confidence Bound"
    short_name = "ucb"
    params = [
        {'title': 'Kappa:', 'name': 'kappa', 'type': 'slide', 'value': 2.576,
         'min': 0.001, 'max': 100, 'subtype': 'log',
         'tip': 'Parameter to indicate how closed are the next parameters sampled.'
                'Higher value = favors spaces that are least explored.'
                'Lower value = favors spaces where the regression function is the '
                'highest.'},
        {'title': 'Kappa actual:', 'name': 'tradeoff_actual', 'type': 'float', 'value': 2.576,
         'tip': 'Current value of the kappa parameter', 'readonly': True},
        {'title': 'Exploration decay:', 'name': 'exploration_decay', 'type': 'float', 'value': 0.9,
         'tip': 'kappa is multiplied by this factor every iteration.'},
        {'title': 'Exploration decay delay:', 'name': 'exploration_decay_delay', 'type': 'int', 'value': 20,
         'tip': 'Number of iterations that must have passed before applying the decay to kappa.'}
    ]
    

    def __init__(self,  **kwargs):
        super().__init__()
        self._function = UpperConfidenceBound(
            kappa=kwargs.get('kappa', 2.576),
            exploration_decay=kwargs.get('exploration_decay', None),
            exploration_decay_delay=kwargs.get('exploration_decay_delay', None),
            random_state=kwargs.get('random_state', None),
        )

    @property
    def tradeoff(self):
        return self._function.kappa

    @tradeoff.setter
    def tradeoff(self, tradeoff):
        self._function.kappa = tradeoff

@GenericAcquisitionFunctionFactory.register()
class GenericProbabilityOfImprovement(GenericAcquisitionFunctionBase):
    usual_name = "Probability of Improvement"
    short_name = "poi"
    params = [ 
        {'title': 'Xi:', 'name': 'xi', 'type': 'slide', 'value': 0,
         'tip': 'Governs the exploration/exploitation tradeoff.'
                'Lower prefers exploitation, higher prefers exploration.'},
        {'title': 'Xi actual:', 'name': 'tradeoff_actual', 'type': 'float', 'value': 2.576,
         'tip': 'Current value of the xi parameter', 'readonly': True},
        {'title': 'Exploration decay:', 'name': 'exploration_decay', 'type': 'float', 'value': 0.9,
         'tip': 'Xi is multiplied by this factor every iteration.'},
        {'title': 'Exploration decay delay:', 'name': 'exploration_decay_delay', 'type': 'int', 'value': 20,
         'tip': 'Number of iterations that must have passed before applying the decay to xi.'}
    ]

    def __init__(self, **kwargs):
        super().__init__()
        self._function = ProbabilityOfImprovement(
            xi=kwargs.get('xi'),
            exploration_decay=kwargs.get('exploration_decay', None),
            exploration_decay_delay=kwargs.get('exploration_decay_delay', None),
            random_state=kwargs.get('random_state', None),
        )

    @property
    def tradeoff(self):
        return self._function.xi

    @tradeoff.setter
    def tradeoff(self, tradeoff):
        self._function.xi = tradeoff

@GenericAcquisitionFunctionFactory.register()
class GenericExpectedImprovement(GenericAcquisitionFunctionBase):
    usual_name = "Expected Improvement"
    short_name = "ei"
    params = [ 
        {'title': 'Xi:', 'name': 'xi', 'type': 'slide', 'value': 0,
         'tip': 'Governs the exploration/exploitation tradeoff.'
                'Lower prefers exploitation, higher prefers exploration.'},
        {'title': 'Xi actual:', 'name': 'tradeoff_actual', 'type': 'float', 'value': 2.576,
         'tip': 'Current value of the xi parameter', 'readonly': True},
        {'title': 'Exploration decay:', 'name': 'exploration_decay', 'type': 'float', 'value': 0.9,
         'tip': 'Xi is multiplied by this factor every iteration.'},
        {'title': 'Exploration decay delay:', 'name': 'exploration_decay_delay', 'type': 'int', 'value': 20,
         'tip': 'Number of iterations that must have passed before applying the decay to xi.'}
    ]
    def __init__(self, **kwargs):
        super().__init__()
        self._function = ExpectedImprovement(
            xi=kwargs.get('xi'),
            exploration_decay=kwargs.get('exploration_decay', None),
            exploration_decay_delay=kwargs.get('exploration_decay_delay', None),
            random_state=kwargs.get('random_state', None),
        )

    @property
    def tradeoff(self):
        return self._function.xi

    @tradeoff.setter
    def tradeoff(self, tradeoff):
        self._function.xi = tradeoff