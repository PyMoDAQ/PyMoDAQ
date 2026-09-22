import numpy as np
from pymodaq_data import Q_

class RampGenerator:
    def __init__(self, start:Q_, end: Q_, duration=Q_(5.0,'s')):
        self.start = start
        self.end = end
        self.duration = duration

    def __call__(self, elapsed_time: Q_) -> Q_:
        return self.update(elapsed_time)

    def update(self, elapsed_time: Q_) -> Q_:
        # Clamp elapsed time to the valid duration window
        t_clamped = np.clip(elapsed_time, Q_(0.0, 's'), self.duration)

        # Linear interpolation for the ramp output
        if self.duration.to_reduced_units().magnitude > 0:
            fraction = (t_clamped / self.duration).to_reduced_units().magnitude
            value = self.start + (self.end - self.start) * fraction
        else:
            value = self.end

        return value