import os
import numpy as np
from datetime import datetime
import pytest
from pathlib import PurePosixPath, Path
from qtpy import QtWidgets, QtCore


import pymodaq.utils.parameter.ioxml
from pymodaq.utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter
from pymodaq.utils import h5modules as h5

import csv





# class TestH5Saver:
#
#     def test_init_file_addhoc(self, get_h5saver, tmp_path):
#         h5saver = get_h5saver
#         addhoc_file_path = tmp_path.joinpath('h5file.h5')
#         h5saver.init_file(update_h5=True, addhoc_file_path=addhoc_file_path,
#                           metadata=dict(attr1='attr1', attr2=(10, 2)))
#         assert h5saver.h5_file_path == addhoc_file_path.parent
#         assert h5saver.h5_file_name == addhoc_file_path.name
#         assert h5saver.settings.child(('current_h5_file')).value() == str(addhoc_file_path)
#         assert h5saver.current_scan_group is None
#         assert h5saver.get_node_path(h5saver.raw_group) == '/Raw_datas'
#         assert h5saver.get_node_path(h5saver.logger_array) == '/Raw_datas/Logger'
#         assert h5saver.get_attr(h5saver.logger_array, 'data_dimension') == '0D'
#         assert h5saver.get_attr(h5saver.logger_array, 'scan_type') == 'scan1D'
#         assert h5saver.get_attr(h5saver.logger_array, 'dtype') == np.dtype(np.uint8).name
#         assert h5saver.get_attr(h5saver.logger_array, 'subdtype') == 'string'
#         assert h5saver.get_last_scan() is None
#         assert h5saver.get_attr(h5saver.raw_group, 'type') == h5saver.settings.child(('save_type')).value()
#         assert h5saver.get_attr(h5saver.root(), 'date') == datetime.now().date().isoformat()
#         assert h5saver.get_attr(h5saver.raw_group, 'attr1') == 'attr1'
#         utils.check_vals_in_iterable(h5saver.get_attr(h5saver.raw_group, 'attr2'), (10, 2))
#
#     def test_init_file(self, get_h5saver_scan, tmp_path):
#         h5saver = get_h5saver_scan
#         datetime_now = datetime.now()
#         date = datetime_now.date()
#         today = f'{date.year}{date.month:02d}{date.day:02d}'
#         base_path = tmp_path
#         h5saver.settings.child(('base_path')).setValue(str(base_path))
#         update_h5 = True
#         scan_path, current_scan_name, save_path = h5saver.update_file_paths(update_h5)
#         assert scan_path == tmp_path.joinpath(str(date.year)).joinpath(today).joinpath(f'Dataset_{today}_000')
#         assert current_scan_name == 'Scan000'
#
#         assert save_path == tmp_path.joinpath(str(date.year)).joinpath(today).joinpath(f'Dataset_{today}_000')
#
#         h5saver.init_file(update_h5=update_h5)
#         assert h5saver.h5_file is h5saver._h5file
#         assert h5saver.h5_file_path.joinpath(f'Dataset_{today}_001.h5').is_file()
#         assert h5saver.get_scan_index() == 0
#
#         h5saver.init_file(update_h5=update_h5)
#         assert h5saver.h5_file_path.joinpath(f'Dataset_{today}_002.h5').is_file()
#         scan_group = h5saver.add_scan_group()
#         assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'
#         assert h5saver.get_scan_index() == 0
#         scan_group1 = h5saver.add_scan_group()
#         assert scan_group == scan_group1  # no increment as no scan_done attribute
#         utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
#                                      sorted(['Logger', 'Scan000']))
#         h5saver.init_file(update_h5=False)
#         utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
#                                      sorted(['Logger', 'Scan000']))
#
#     def test_load_file(self, get_h5saver_scan, tmp_path):
#         h5saver = get_h5saver_scan
#         h5saver.settings.child(('base_path')).setValue(str(tmp_path))
#         h5saver.init_file(update_h5=True)
#         h5saver.close_file()
#         file_path = h5saver.settings.child(('current_h5_file')).value()
#
#         h5saver.load_file(file_path=file_path)
#         assert h5saver.file_loaded
#
#     def test_groups(self, get_h5saver_scan, tmp_path):
#         h5saver = get_h5saver_scan
#         base_path = tmp_path
#         h5saver.settings.child(('base_path')).setValue(base_path)
#         update_h5 = True
#         h5saver.init_file(update_h5=update_h5)
#         scan_group = h5saver.add_scan_group(settings_as_xml='this is a setting',
#                                             metadata=dict(attr1='blabla', attr2=1.1, pixmap2D='invalid pixmap'))
#         assert h5saver.get_scan_index() == 0
#         assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'
#         scan_group = h5saver.add_scan_group()
#         # if no child in scan group no incrementation
#         assert h5saver.get_scan_index() == 0
#         assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'
#
#         ch1_group = h5saver.add_CH_group(scan_group)
#         assert h5saver.get_node_path(ch1_group) == '/Raw_datas/Scan000/Ch000'
#         assert h5saver.get_set_group(scan_group, 'Ch000') == h5saver.current_group
#         assert h5saver.get_scan_index() == 0
#         h5saver.set_attr(scan_group, 'scan_done', True)
#         assert h5saver.get_scan_index() == 1
#
#         scan_group_1 = h5saver.add_scan_group()
#         assert h5saver.get_scan_index() == 1
#         h5saver.set_attr(scan_group_1, 'scan_done', True)
#         assert h5saver.get_scan_index() == 2
#         ch1_group_1 = h5saver.add_CH_group(scan_group_1)
#         assert h5saver.get_scan_index() == 2
#         assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan001'
#
#     def test_hierarchy(self, get_h5saver_scan, tmp_path):
#         h5saver = get_h5saver_scan
#         base_path = tmp_path
#         h5saver.settings.child(('base_path')).setValue(base_path)
#         h5saver.init_file(update_h5=True)
#         scan_group = h5saver.add_scan_group()
#         h5saver.add_det_group(scan_group)
#         h5saver.add_det_group(scan_group)
#         move_group = h5saver.add_move_group(scan_group)
#         assert h5saver.get_node_path(move_group) == '/Raw_datas/Scan000/Move000'
#         det_group = h5saver.add_det_group(scan_group)
#         for data_type in group_data_types:
#             data_group = h5saver.add_data_group(det_group, data_type)
#             assert h5saver.get_node_name(data_group) == utils.capitalize(data_type)
#             CH_group0 = h5saver.add_CH_group(data_group)
#             assert h5saver.get_node_path(
#                 CH_group0) == f'/Raw_datas/Scan000/Detector002/{utils.capitalize(data_type)}/Ch000'
#             CH_group1 = h5saver.add_CH_group(data_group)
#             assert h5saver.get_node_path(
#                 CH_group1) == f'/Raw_datas/Scan000/Detector002/{utils.capitalize(data_type)}/Ch001'
#
#         live_group = h5saver.add_live_scan_group(scan_group, '0D')
#         assert h5saver.get_node_path(live_group) == '/Raw_datas/Scan000/Live_scan_0D'
#
#     def test_data_save(self, get_h5saver_scan, tmp_path):
#         h5saver = get_h5saver_scan
#         base_path = tmp_path
#         h5saver.settings.child(('base_path')).setValue(base_path)
#         h5saver.init_file(update_h5=True)
#         scan_group = h5saver.add_scan_group()
#         det_group = h5saver.add_det_group(scan_group)
#         data_group = h5saver.add_data_group(det_group, 'data2D')
#         CH_group0 = h5saver.add_CH_group(data_group)
#         CH_group1 = h5saver.add_CH_group(data_group)
#
#         xaxis = dict(data=np.linspace(0, 5, 6), label='x_axis_label', units='x_axis_units')
#         yaxis = dict(data=np.linspace(10, 20, 11), label='y_axis_label', units='custom')
#         data_dict = dict(data=np.random.rand(len(xaxis['data']), len(yaxis['data'])), x_axis=xaxis,
#                          y_axis=yaxis)
#         array = h5saver.add_data(CH_group0, data_dict, scan_type='', enlargeable=False)
#         assert h5saver.is_node_in_group(CH_group0, 'Data')
#         assert np.all(h5saver.get_attr(array, 'shape') == data_dict['data'].shape)
#         assert array.attrs['type'] == 'data'
#         assert h5saver.get_attr(array, 'data_dimension') == '2D'
#         assert array.attrs['scan_type'] == ''
#
#         nav_x_axis = dict(data=np.linspace(0, 2, 3), label='navigation', units='custom')
#         data_dict = dict(data=np.random.rand(len(xaxis['data']), len(yaxis['data'])), x_axis=xaxis,
#                          y_axis=yaxis, nav_x_axis=nav_x_axis)
#
#         array = h5saver.add_data(CH_group1, data_dict, init=True, scan_type='scan1D',
#                                  scan_shape=nav_x_axis['data'].shape,
#                                  enlargeable=False, add_scan_dim=True)
#         assert h5saver.is_node_in_group(CH_group1, 'Data')
#         assert np.all(h5saver.get_attr(array, 'shape') == (len(nav_x_axis['data']),
#                                                            len(xaxis['data']), len(yaxis['data'])))
#         assert array.attrs['type'] == 'data'
#         assert array.attrs['data_dimension'] == '2D'
#         assert array.attrs['scan_type'] == 'scan1D'
#         assert np.all(h5saver.read(array).shape == (len(nav_x_axis['data']), len(xaxis['data']), len(yaxis['data'])))
#         assert h5saver.is_node_in_group(CH_group1, 'X_axis')
#         xnode = h5saver.get_node(CH_group1, 'X_axis')
#         assert xnode.attrs['type'] == 'axis'
#         assert xnode.attrs['label'] == 'x_axis_label'
#         assert xnode.attrs['units'] == 'x_axis_units'
#         assert xnode.attrs['data_dimension'] == '1D'
#         assert xnode.attrs['scan_type'] == ''
#
#         assert h5saver.is_node_in_group(CH_group1, 'Y_axis')
#
#         assert h5saver.is_node_in_group(CH_group1, 'Nav_x_axis')
#         navnode = h5saver.get_node(CH_group1, 'Nav_x_axis')
#         assert navnode.attrs['type'] == 'axis'
#         assert navnode.attrs['label'] == 'navigation'
#         assert navnode.attrs['units'] == 'custom'
#         assert navnode.attrs['data_dimension'] == '1D'
#         assert navnode.attrs['scan_type'] == ''
#
#         # test enlargeable array
#         CH_group2 = h5saver.add_CH_group(data_group)
#         dshape = (10,)
#         array = h5saver.add_array(CH_group2, 'earray', data_type='data', data_shape=dshape, data_dimension='1D',
#                                   array_type=np.uint32,
#                                   enlargeable=True)
#         assert h5saver.is_node_in_group(CH_group2, 'earray')
#         assert array.attrs['CLASS'] == 'EARRAY'
#         array.append(np.random.rand(*dshape))
#         array.append(np.random.rand(*dshape))
#         assert np.all(h5saver.read(array).shape == (2, 10))
#
#
# @pytest.fixture(params=tested_backend)
# def create_test_file(request, qtbot):
#     bck = h5.H5Saver(backend=request.param)
#     basepath = Path(__file__).parent
#     filepath = basepath.joinpath(f'data/data_test_{request.param}.h5')
#     bck.init_file(update_h5=True, addhoc_file_path=filepath)
#
#     Nx = 12
#     Nnavx = 5
#     Nnavy = 10
#     scan_shape = (Nnavx, Nnavy)
#     x_axis = dict(label='this is data axis', units='no units', data=np.arange(Nx))
#     data1D = dict(data=np.arange(Nx) * 1.0 + 7, x_axis=x_axis)
#
#     nav_x_axis = dict(label='this is nav x axis', units='x units', data=np.arange(Nnavx), nav_index=0)
#     nav_y_axis = utils.NavAxis(label='this is nav y axis', units='y units', data=np.arange(Nnavy), nav_index=1)
#
#     d = datetime(year=2020, month=5, day=24, hour=10, minute=52, second=55)
#
#     raw_group = bck.add_group('Agroup', 'data', '/',
#                               metadata=dict(date_time=d, author='Seb Weber',
#                                             settings='this should be xml',
#                                             scan_settings=b'scan binary setting',
#                                             type='scan',
#                                             shape=(10, 45),
#                                             pixmap_1D=b'this should be binary png in reality',
#                                             pixmap_2D=b'this should be another binary png in reality'))
#
#     bck.add_data(raw_group, data1D)
#
#     scan_group = bck.add_scan_group('first scan', settings_as_xml='this should dbe xml settings')
#     params = [
#         {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
#             {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
#                 'readonly': True},
#             {'title': 'Detector type:', 'name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
#             {'title': 'Nviewers:', 'name': 'Nviewers', 'type': 'int', 'value': 1, 'min': 1, 'default': 1,
#              'readonly': True},
#         ]
#         }
#     ]
#     settings = Parameter.create(name='settings', type='group', children=params)
#     settings_xml = pymodaq.utils.parameter.ioxml.parameter_to_xml_string(settings)
#
#     det_group = bck.add_det_group(scan_group, 'det group', settings_as_xml=settings_xml)
#     data_group = bck.add_data_group(det_group, 'data1D')
#     ch_group = bck.add_CH_group(data_group)
#
#     data = np.arange(Nx * Nnavx * Nnavy)
#     data = data.reshape(Nnavx, Nnavy, Nx)
#     data_dict = dict(data=data, x_axis=x_axis)
#
#     bck.add_data(ch_group, data_dict, scan_type='scan2D', scan_shape=scan_shape, add_scan_dim=False)
#     bck.add_navigation_axis(nav_x_axis.pop('data'), scan_group, 'x_axis', metadata=nav_x_axis)
#     bck.add_navigation_axis(nav_y_axis.pop('data'), scan_group, 'y_axis', metadata=nav_y_axis)
#
#     bck.logger_array.append('log1 to check')
#     bck.logger_array.append('log2 to check')
#
#     bck.close_file()
#     return bck
#
#
# @pytest.fixture(params=tested_backend)
# def get_file(request):
#     basepath = Path(__file__).parent
#     filepath = basepath.joinpath(f'data/data_test_{request.param}.h5')
#     return filepath
#
#
# @pytest.fixture(params=tested_backend)
# def load_test_file(request, get_file):
#     bck = H5BrowserUtil(backend=request.param)
#     bck.open_file(get_file, 'r')
#     return bck
#
#
# class TestH5BrowserUtil:
#
#     def test_create(self, create_test_file):
#         """Create "same" files using all backends"""
#         create_test_file
#
#     def test_get_h5_attributes(self, load_test_file):
#         """Load files (created with all backends) and manipulate them using all backends"""
#         h5utils = load_test_file
#
#         node_path = '/Agroup'
#         node = h5utils.get_node(node_path)
#         assert node.attrs['date_time'] == datetime(year=2020, month=5, day=24, hour=10, minute=52, second=55)
#         assert node.attrs['shape'] == (10, 45)
#
#         attr_dict, settings, scan_settings, pixmaps = h5utils.get_h5_attributes(node_path)
#         assert settings == 'this should be xml'
#         assert scan_settings == b'scan binary setting'
#         for attr in ['CLASS', 'TITLE', 'author', 'date_time', 'settings', 'scan_settings', 'type', 'shape',
#                      'pixmap_1D', 'pixmap_2D']:
#             assert attr in node.attrs.attrs_name
#         assert len(pixmaps) == 2
#         assert pixmaps[0] == b'this should be binary png in reality'
#         assert pixmaps[1] == b'this should be another binary png in reality'
#
#         node_path = '/Raw_datas/Scan000/Detector000/Data1D/Ch000/Data'
#         node = h5utils.get_node(node_path)
#         attr_dict, settings, scan_settings, pixmaps = h5utils.get_h5_attributes(node_path)
#         assert attr_dict['data_dimension'] == 'ND'
#         assert attr_dict['dtype'] == 'int32'
#         assert attr_dict['scan_type'] == 'scan2D'
#         assert attr_dict['shape'] == (5, 10, 12)
#         assert attr_dict['type'] == 'data'
#
#         node_path = '/Raw_datas/Logger'
#         node = h5utils.get_node(node_path)
#         attr_dict, settings, scan_settings, pixmaps = h5utils.get_h5_attributes(node_path)
#         assert attr_dict['data_dimension'] == '0D'
#         assert attr_dict['dtype'] == 'uint8'
#         assert attr_dict['scan_type'] == 'scan1D'
#         assert attr_dict['shape'] == (2,)
#         assert attr_dict['subdtype'] == 'string'
#         assert attr_dict['type'] == 'log'
#         h5utils.close_file()
#
#     def test_get_h5_data(self, load_test_file):
#         """Load files (created with all backends) and manipulate them using
#          all backends for cross compatibility checks
#          """
#         h5utils = load_test_file
#         node_path = '/Raw_datas/Logger'
#         node = h5utils.get_node(node_path)
#         assert isinstance(node, StringARRAY)
#         data, axes, nav_axes, is_spread = h5utils.get_h5_data(node_path)
#         assert isinstance(data, list)
#         assert len(data) == 2
#         assert data[0] == 'log1 to check'
#         assert data[1] == 'log2 to check'
#         assert axes == []
#         assert nav_axes == []
#
#         Nx = 12
#         Nnavx = 5
#         Nnavy = 10
#         x_axis_in_file = dict(label='this is data axis', units='no units', data=np.arange(Nx))
#         nav_x_axis_in_file = dict(label='this is nav x axis', units='x units', data=np.arange(Nnavx))
#         nav_y_axis_in_file = dict(label='this is nav y axis', units='y units', data=np.arange(Nnavy))
#         data_in_file = np.arange(Nx * Nnavx * Nnavy)
#         data_in_file = data_in_file.reshape(Nnavx, Nnavy, Nx)
#
#         node_path = '/Agroup'
#         node = h5utils.get_node(node_path)
#         assert len(node.children()) == 2
#         assert node.children_name() == ['Data', 'X_axis']
#         node_path = '/Agroup/Data'
#         data, axes, nav_axes, is_spread = h5utils.get_h5_data(node_path)
#         assert np.all(data == pytest.approx(np.arange(Nx) * 1.0 + 7))
#
#         node_path = '/Raw_datas/Scan000/Detector000/Data1D/Ch000/Data'
#         node = h5utils.get_node(node_path)
#         data, axes, nav_axes, is_spread = h5utils.get_h5_data(node_path)
#         assert isinstance(data, np.ndarray)
#         assert data.shape == (5, 10, 12)
#         assert node.attrs['shape'] == (5, 10, 12)
#         assert np.all(data == data_in_file)
#
#         assert len(axes) == 4
#         assert len(nav_axes) == 2
#         utils.check_vals_in_iterable(nav_axes, [0, 1])
#         assert axes['x_axis']['label'] == x_axis_in_file['label']
#         assert axes['x_axis']['units'] == x_axis_in_file['units']
#         assert np.all(axes['x_axis']['data'] == x_axis_in_file['data'])
#         assert isinstance(axes['x_axis'], utils.Axis)
#         assert isinstance(axes['x_axis'], dict)
#
#         assert axes['nav_00']['label'] == nav_x_axis_in_file['label']
#         assert axes['nav_00']['units'] == nav_x_axis_in_file['units']
#         assert np.all(axes['nav_00']['data'] == nav_x_axis_in_file['data'])
#
#         assert axes['nav_01']['label'] == nav_y_axis_in_file['label']
#         assert axes['nav_01']['units'] == nav_y_axis_in_file['units']
#         assert np.all(axes['nav_01']['data'] == nav_y_axis_in_file['data'])
#         h5utils.close_file()
#
#     def test_export_h5_data(self, load_test_file):
#         """Load files (created with all backends) and manipulate them using
#          all backends for cross compatibility checks
#          """
#         h5utils = load_test_file
#         node_path = '/Raw_datas/Logger'
#         node = h5utils.get_node(node_path)
#         data = node.read()
#         h5utils.export_data(node_path, '/data/stringdata.txt')
#         with open('/data/stringdata.txt', 'r') as f:
#             reader = csv.reader(f)
#             data_back = []
#             for row in reader:
#                 data_back.append(row[0])
#
#         assert data_back == data
#         os.remove('/data/stringdata.txt')
#
#         node_path = '/Raw_datas/Scan000/Detector000/Data1D/Ch000/X_axis'
#         node = h5utils.get_node(node_path)
#         data = node.read()
#         h5utils.export_data(node_path, '/data/data.txt')
#         data_back = np.loadtxt('/data/data.txt')
#         assert np.all(data == pytest.approx(data_back))
#         os.remove('/data/data.txt')
#
#         node_path = '/Agroup'
#         h5utils.export_data(node_path, '/data/data.txt')  # export both Data and X_axis node
#
#         xaxis = h5utils.get_node('/Agroup/X_axis').read()
#         data = h5utils.get_node('/Agroup/Data').read()
#
#         data_back = np.loadtxt('/data/data.txt')
#         assert np.all(xaxis == pytest.approx(data_back[:, 1]))
#         assert np.all(data == pytest.approx(data_back[:, 0]))
#         os.remove('/data/data.txt')
#
#         h5utils.close_file()
#
#
# @pytest.fixture(params=tested_backend)
# def load_test_file_h5browser(request, get_file, qtbot):
#     win = QtWidgets.QMainWindow()
#     h5browser = H5Browser(win, h5file_path=get_file, backend=request.param)
#     win.show()
#     qtbot.addWidget(win)
#     return h5browser
#
#
# class TestH5Browser:
#
#     def test_create(self, create_test_file):
#         """Create "same" files using all backends"""
#         create_test_file
#
#     def test_h5browser(self, load_test_file_h5browser, qtbot):
#         h5browser = load_test_file_h5browser
#
#         item = h5browser.ui.h5file_tree.treewidget.findItems(
#             'Agroup', QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)[0]
#         assert item.text(2) == '/Agroup'
#         h5browser.ui.h5file_tree.treewidget.setCurrentItem(item)
#
#         node = h5browser.h5utils.get_node('/Agroup')
#         qtbot.mouseClick(h5browser.ui.h5file_tree.treewidget, QtCore.Qt.LeftButton)
#
#         for child in h5browser.settings_raw.children():
#             assert child.name in node.attrs.attrs_name
#
#         node_path = '/Raw_datas/Scan000/Detector000/Data1D/Ch000/X_axis'
#         node = h5browser.h5utils.get_node(node_path)
#         items = h5browser.ui.h5file_tree.treewidget.findItems('X_axis',
#                                                               QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
#         item = [it for it in items if it.text(2) == node_path][0]
#         h5browser.ui.h5file_tree.treewidget.setCurrentItem(item)
#
#         qtbot.mouseClick(h5browser.ui.h5file_tree.treewidget, QtCore.Qt.LeftButton)
#
#         for child in h5browser.settings_raw.children():
#             assert child.name in node.attrs.attrs_name
#
#         node.attrs['comments'] = ''  # mandatory for cross testing
#         h5browser.add_comments(False, comment='this is a comment.')
#         assert node.attrs['comments'] == 'this is a comment.'
#         h5browser.add_comments(False, comment=' This is a second comment')
#         h5browser.h5utils.flush()
#         assert node.attrs['comments'] == 'this is a comment. This is a second comment'
#
#         h5browser.h5utils.close_file()
