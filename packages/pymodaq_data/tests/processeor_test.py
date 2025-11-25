import numpy as np

from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory
from pymodaq_data.data import DataRaw, Axis

from pymodaq_utils import math_utils as mutils

processors = DataProcessorFactory()


config_processors = {
}


print('Builders:\n'
      f'{processors.builders}')

print('Math functions:\n'
      f'{processors.functions}')

# test 2D signals
Nsigx = 200
Nsigy = 100
Nnav = 10
x = np.linspace(-Nsigx / 2, Nsigx / 2 - 1, Nsigx)
y = np.linspace(-Nsigy / 2, Nsigy / 2 - 1, Nsigy)

dat = np.zeros((Nnav, Nsigy, Nsigx))
for ind in range(Nnav):
    dat[ind] = ind * mutils.gauss2D(x, 10 * (ind - Nnav / 2), 25 / np.sqrt(2),
                                    y, 2 * (ind - Nnav / 2), 10 / np.sqrt(2))

data = DataRaw('mydata', data=[dat], nav_indexes=(0,),
               axes=[Axis('nav', data=np.linspace(0, Nnav -1, Nnav), index=0),
                     Axis('sigy', data=y, index=1),
                     Axis('sigx', data=x, index=2)])
new_data = processors.get('sum', **config_processors).operate(data.isig[25:75, 75:125])
print(new_data)
print(new_data.data)
