import numpy as np

from pymodaq.extensions.data_mixer.model import DataMixerModel, np  # np will be used in method eval of the formula

from pymodaq_utils.math_utils import gauss1D, my_moment

from pymodaq_data.data import DataToExport, DataWithAxes, DataCalculated
from pymodaq_gui.parameter import Parameter

from pymodaq.extensions.data_mixer.parser import (
    extract_data_names, split_formulae, replace_names_in_formula)


def gaussian_fit(x, amp, x0, dx, offset):
    dx = np.abs(dx)
    return amp * gauss1D(x, x0, dx) + offset


class DataMixerModelFit(DataMixerModel):
    params = [

    ]

    def ini_model(self):
        pass

    def update_settings(self, param: Parameter):
        pass

    def process_dte(self, dte: DataToExport):
        dte_processed = DataToExport('computed')
        dwa = dte.get_data_from_full_name('Det 01/mymock').deepcopy()
        dwa_fit = dwa.fit(gaussian_fit, self.get_guess(dwa))
        dwa.append(dwa_fit)
        dte_processed.append(dwa)
        dte_processed.append(
            DataCalculated('Coeffs',
                           data=[np.atleast_1d(coeff) for coeff in dwa_fit.fit_coeffs[0]],
                           labels=['amp', 'x0', 'dx', 'offset']))

        return dte_processed

    @staticmethod
    def get_guess(dwa):
        offset = np.min(dwa).value()
        moments = my_moment(dwa.axes[0].get_data(), dwa.data[0])
        amp = (np.max(dwa) - np.min(dwa)).value()
        x0 = float(moments[0])
        dx = float(moments[1])

        return amp, x0, dx, offset


