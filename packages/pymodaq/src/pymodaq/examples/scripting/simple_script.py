from pathlib import Path

from pymodaq_data import Q_
from pymodaq_data.h5modules.backends import GroupType

from pymodaq.scripting import Detector, Actuator
from pymodaq_data.h5modules.data_saving import DataToExportEnlargeableSaver

theta = Actuator('Angle')
det0d = Detector('Det0D')
det1d = Detector('Det1D')

acquisitions = []

base = theta.get_actuator_value().result()
target = base + Q_('90°')  # Or a DataActuator(data=90, units='°')
step = Q_('10°')

count = (target - base)/step
count = int(count.quantities[0].m[0]) + 1

filename = Path(r'C:\Data\2026\scripted_data1.h5')

with DataToExportEnlargeableSaver(filename, enl_axis_names=('count',), enl_axis_units=('',)) as saver:

    group = saver.add_group('Script', group_type=GroupType.data ,where='/RawData/', title='scripted_data')
    group0d = saver.add_det_group(where=group, title=det0d.name)
    group1d = saver.add_det_group(where=group, title=det1d.name)
    for idx in range(count):
        value = theta.move_abs(base + idx * step).result()  # taking directly the result makes it a blocking move
        dte0d_future = det0d.snap()  # async snap
        dte1d_future = det1d.snap()  # async snap
        saver.add_data(group0d, dte0d_future.result(), (value.value(), ))
        saver.add_data(group1d, dte1d_future.result(), (value.value(),))

