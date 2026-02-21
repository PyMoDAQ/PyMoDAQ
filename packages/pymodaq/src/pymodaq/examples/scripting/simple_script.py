from pathlib import Path

from pymodaq_data import Q_, DataDim
from pymodaq.scripting import Detector, Actuator

from pymodaq_data.h5modules.data_saving import DataToExportEnlargeableSaver

theta = Actuator('Angle')
det0d = Detector('Det0D')

acquisitions = []

base = theta.get_actuator_value().result()
target = base + Q_('90°') # Or a DataActuator(data=90, units='°')
step = Q_('10°')

count = (target - base)/step
count = int(count.quantities[0].m[0]) + 1

filename = Path(r'C:\Data\2026\scripted_data4.h5')

with DataToExportEnlargeableSaver(filename, enl_axis_names=('count',), enl_axis_units=('',)) as saver:
    group = saver.add_data_group('/RawData/', DataDim.Data2D, title='scripted_data', group_name='Script')
    value = base

    for idx in range(1, count + 1):
        acquisitions.append((value, det0d.snap().result()))

        value = theta.move_abs(base + idx * step)

        saver.add_data(group, acquisitions[-1][1], (value.result().value(),))





print(acquisitions)