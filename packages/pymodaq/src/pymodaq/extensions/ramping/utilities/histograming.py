from dataclasses import dataclass, field

import numpy as np

from pathlib import Path

from qtpy import QtCore
from qtpy.QtCore import QObject

from pymodaq_gui.utils.app_worker import ProcessorWorker

from pymodaq_gui.managers.h5manager import H5Manager
from pymodaq_gui.managers.runner_thread_manager import DataForProcessor, get_thread_params
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport, DataWithAxes, DataCalculated, Axis, DataDistribution, DataDim
from pymodaq_data.h5modules.data_saving import DataLoader, GROUP

from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_utils.math_utils import find_index


logger = set_logger(get_module_name(__file__))


class H5Histogramming(QObject, ParameterManager):
    params = [
        {'title': 'H5:', 'name': 'h5info', 'type': 'group', 'children': [
            {'title': 'H5 Path:', 'name': 'h5path', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Node:', 'name': 'node_path', 'type': 'list', 'limits': [],},

        ]},
        {'title': 'Histo:', 'name': 'histo', 'type': 'group', 'children': [
            {'title': 'Ramping Actuator:', 'name': 'actuator', 'type': 'list', },
            {'title': 'Detectors to Plot:', 'name': 'detectors', 'type': 'itemselect', 'checkbox': True},
            {'title': 'Actuators to Plot:', 'name': 'actuators', 'type': 'itemselect', 'checkbox': True},
            {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': 500.},
            {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': 560.},
            {'title': 'AutoBin:', 'name': 'autobin', 'type': 'bool', 'value': True},
            {'title': 'Nbin:', 'name': 'nbins', 'type': 'int', 'value': 100, 'readonly': False},
        ]},
        {'title': 'Compute Histogram', 'name': 'compute_histogram', 'type': 'action'}
    ]

    def __init__(self, h5_manager: H5Manager, viewer: ViewerDispatcher, parent=None):
        QObject.__init__(self, parent)
        ParameterManager.__init__(self)

        self._h5_manager = h5_manager
        self._viewer = viewer
        self._actuators: dict[str, str] = {}
        self._detectors: dict[str, str] = {}
        self._data_loader: DataLoader = None

        self._histogram_processor: HistogramProcessor = None

        self._h5_manager.file_loaded_signal.connect(self.update_settings_from_file)

        self.settings.child('compute_histogram').setOpts(enabled=False)
        self.settings.child('compute_histogram').sigActivated.connect(self.update_histogramer)

    @property
    def histogram_processor(self) -> 'HistogramProcessor':
        if self._histogram_processor is None:
            self._histogram_processor = HistogramProcessor(self._h5_manager.h5saver)
            self._histogram_processor.nbins_signal.connect(
                self.settings.child('histo', 'nbins').setValue)


            self._histogram_processor.data_processed_signal.connect(self._viewer.show_data)
        return self._histogram_processor

    def update_histogramer(self):
        self.histogram_processor.data_to_process_signal.emit(
            InfoForHistogram(self.settings['h5info', 'node_path'],
                             xaxis_name=self.settings['histo', 'actuator'],
                             start=self.settings['histo', 'start'],
                             stop=self.settings['histo', 'stop'],
                             other_names=self.settings['histo', 'actuators']['selected'] +
                                         self.settings['histo', 'detectors']['selected'],
                             bins='auto' if self.settings['histo', 'autobin'] else
                             self.settings['histo', 'nbins'],
                             )
        )

    def update_settings_from_file(self, file_path: Path):
        """ Offline mode. Means ramping is not in progress and the h5file was closed and has
        been opened for here
        """
        self.settings.child('compute_histogram').setOpts(enabled=True)
        node_param = self.settings.child('h5info', 'node_path')

        self._data_loader = DataLoader(self._h5_manager.h5saver,
                                       swmr_mode=False)
        self.settings['h5info', 'h5path'] = str(file_path)
        nodes = self.get_main_nodes()
        with self.settings.treeChangeBlocker(keep=set()):
            self.settings.child('h5info', 'node_path').setValue(node_param)
            node_param.setLimits(nodes)
            node_param.setValue(nodes[-1] if len(nodes) > 0 else None)

        self._on_node_path_change()

        self.update_histogramer()

    @property
    def data_loader(self) -> DataLoader:
        return DataLoader(self._h5_manager.h5saver, swmr_mode=True)

    def get_main_nodes(self) -> list[str | GROUP]:
        nodes = []
        for ind, _node in enumerate(self.data_loader.walk_nodes('/RawData', depth=1, only_groups=True)):
            if ind > 0:
                nodes.append(_node.path)
        return nodes

    def get_actuators(self, main_node: str | GROUP) -> dict[str, str]:
        self._actuators = {}
        for ind, node in enumerate(self.data_loader.walk_nodes(main_node, depth=1, only_groups=True)):
            if ('type' in node.attrs and node.attrs['type'] == 'actuator' and
                    len(node.children()) > 0):
                self._actuators[node.title] = node.path
        return self._actuators

    def get_detectors(self, main_node: str | GROUP) -> dict[str, str]:
        self._detectors = {}
        for ind, node in enumerate(self.data_loader.walk_nodes(main_node, depth=1, only_groups=True)):
            if ('type' in node.attrs and node.attrs['type'] == 'detector' and
                    len(node.children()) > 0):
                self._detectors[node.title] = node.path
        return self._detectors

    def get_actuator_dwa(self, actuator_name: str) -> DataWithAxes:
        return self.data_loader.load_all(self._actuators[actuator_name])[0]

    def get_detector_dte(self, detector_name: str) -> DataToExport:
        return self.data_loader.load_all(self._actuators[detector_name], with_bkg=False)

    def _on_node_path_change(self):
        self.update_control_modules()
        bin_size = self.check_min_axis_size()

        if bin_size is None:
            self.settings['histo', 'autobin'] = True
        else:
            self.settings['histo', 'nbins'] = bin_size

    def _on_actuator_changed(self, actuator_name: str):
        self.get_set_bounds(actuator_name)

    def value_changed(self, param: Parameter):
        if param.name() == 'node_path':
            self._on_node_path_change()

        elif param.name() == 'actuator':
            if param.value() in self._actuators:
                self._on_actuator_changed(param.value())

        elif param.name()  == 'autobin':
            self.settings.child('histo', 'nbins').setReadonly(param.value())

        self.update_histogramer()

    def get_set_bounds(self, actuator_name: str):
        dwa = self.data_loader.load_all(where=self._actuators[actuator_name])[0]
        self.settings.child('histo', 'start').setLimits((np.min(dwa[0]), np.max(dwa[0])))
        self.settings.child('histo', 'stop').setLimits((np.min(dwa[0]), np.max(dwa[0])))
        self.settings['histo', 'start'] = np.min(dwa[0])
        self.settings['histo', 'stop'] = np.max(dwa[0])

    def update_control_modules(self):

        group_histo = self.settings.child('histo')
        actuator_param = self.settings.child('histo', 'actuator')

        actuators = self.get_actuators(self.settings['h5info', 'node_path'])
        detectors = self.get_detectors(self.settings['h5info', 'node_path'])

        actuators_name = list(actuators.keys())
        detectors_name = list(detectors.keys())

        if self.settings['histo', 'actuator'] not in actuators_name:
            actuator_name = actuators_name.pop(0)
        else:
            actuator_name = self.settings['histo', 'actuator']
            actuators_name.remove(self.settings['histo', 'actuator'])

        with self.settings.treeChangeBlocker(keep=set()):
            group_histo.child('actuator').setOpts(limits=[actuator_name] + actuators_name)

            group_histo.child('actuators').setValue(dict(all_items=actuators_name,
                                                                    selected=actuators_name, ))
            group_histo.child('detectors').setValue(dict(all_items=detectors_name,
                                                                    selected=detectors_name, ))
            group_histo.child('actuator').setValue(actuator_name)

        self._on_actuator_changed(actuator_name)


    def get_data(self):

        x_dwa = self.get_actuator_dwa(self.settings['histo', 'actuator'])
        dte_0d = DataToExport('Data0D')
        for actuator in self.settings['histo', 'actuators']['selected']:
            dte_0d.append(self.get_actuator_dwa(actuator))
        for detector in self.settings['histo', 'detectors']['selected']:
            dte_0d.append(self.get_detector_dte(detector).get_data_from_dim(DataDim.Data0D))

    def check_min_axis_size(self) -> int | None:
        """ Look at the arrays under current node for the minimal navigation size"""
        min_size = None
        for ind, node in enumerate(self.data_loader.walk_nodes(self.settings['h5info', 'node_path'])):
            if 'shape' in node.attrs:
                if min_size is None:
                    min_size = node.attrs['shape'][0]
                else:
                    min_size = min(min_size, node.attrs['shape'][0])
        return min_size

@dataclass
class InfoForHistogram(DataForProcessor):
    xaxis_name: str

    start: float
    stop: float
    other_names: list[str] = field(default_factory=list)

    bins: float | str = 'auto'



class HistogramProcessor(ProcessorWorker):

    worker_setting_name: str = 'histogram_worker'
    nbins_signal = QtCore.Signal(int)
    params = get_thread_params(worker_setting_name)

    def __init__(self, h5saver: H5Saver, parent=None):
        super().__init__(h5saver=h5saver, parent=parent)

    def do_process_data(self, info: InfoForHistogram):
        dte_out = DataToExport('DataOut')
        try:
            dte_out = self.compute_histogram(info)
        finally:
            self.data_processed_signal.emit(dte_out)
            self._n_jobs_done += 1
            self.n_jobs_done_signal.emit(self.name, self._n_jobs_done)

    def compute_histogram(self, info: InfoForHistogram) -> DataToExport:
        dte_out = DataToExport('DataOut')
        dte = self._data_loader.load_all(where=info.node_path)
        if len(dte) >= 2: # one for the xaxis and the other(s) for the y axes
            xdwa = dte.pop(dte.index_from_name_origin(info.xaxis_name))

            ((istart, vstart), (istop, vstop)) = find_index(
                xdwa[0], threshold=[info.start, info.stop])

            nav_index = xdwa.nav_indexes[0]
            try:
                xdwa_sliced = xdwa.inav[istart:istop]
            except IndexError:
                xdwa_sliced = xdwa

            # first compute bins from one of the varying signals
            timestamps_axis = xdwa_sliced.get_axis_from_index(nav_index)[0]
            if timestamps_axis is not None and timestamps_axis.size > 1:
                timestamps = timestamps_axis.get_data()
                if info.bins == 'auto':
                    nbins = len(np.histogram_bin_edges(dte[0][0], 'auto')) + 1
                else:
                    nbins = info.bins

                bin_edges = np.histogram_bin_edges(timestamps, bins=nbins)

                if info.bins == 'auto':
                    self.nbins_signal.emit(len(bin_edges) - 1)

                # then compute the bin index for each timestamp
                indexes = np.digitize(timestamps, bin_edges)

                # average actuator data in their corresponding bins:
                averaged_actuator_values = np.atleast_1d(
                    self.average_data_over_indexes(xdwa[0], indexes))

                nans = np.isnan(averaged_actuator_values)

                for dwa in dte:
                    indexes = np.digitize(dwa.get_axis_from_index(nav_index)[0].get_data(), bin_edges)
                    arrays = [np.delete(
                        np.atleast_1d(
                        self.average_data_over_indexes(dwa[ind],
                                                       indexes,
                                                       len(averaged_actuator_values)-1)),
                        nans, axis=0) for ind in range(len(dwa))]
                    try:
                        dwa_processed = DataCalculated(
                            dwa.name, origin=dwa.origin,
                            data = arrays,
                            axes = [Axis(label=xdwa.name, units=xdwa.units,
                                         data=np.delete(averaged_actuator_values,
                                                        nans, axis=0),
                                         index=nav_index)] +
                                   [dwa.get_axis_from_index(ind)[0] for ind in dwa.sig_indexes],
                            labels=dwa.labels,
                            units = dwa.units,
                            nav_indexes=(nav_index,) if len(dwa.sig_indexes) > 0 else ( ),
                            distribution=DataDistribution.uniform,
                        )
                        dte_out.append(dwa_processed)
                    except IndexError as e:
                        pass
        return dte_out


    @staticmethod
    def average_data_over_indexes(data: np.ndarray[float],
                                  indexes: np.ndarray[int],
                                  index_max: int = None) -> np.ndarray[float]:
        """ Return the average  of data over the indexes

        See: https://stackoverflow.com/questions/71329884/python-numpy-get-average-of-array-based-on-index
        """
        if index_max is None:
            index_max = indexes.max()
        res = np.linspace(0, indexes.max(), index_max + 1)
        try:

            one_hot = np.eye(index_max + 1)[indexes]

            counts = np.sum(one_hot, axis=0)
            one_hot_t = one_hot.T
            for ind in range(len(data.shape) - len(one_hot_t.shape) + 1):
                one_hot_t = np.expand_dims(one_hot_t, axis=ind+2)
                counts = np.expand_dims(counts, axis=ind+1)
            res = np.sum((one_hot_t * data[0:len(indexes)]), axis=1) / counts
        except (ValueError, IndexError) as e:
            pass
        return res

