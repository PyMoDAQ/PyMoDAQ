# -*- coding: utf-8 -*-
"""
Created the 28/03/2023

@author: Sebastien Weber
"""
import numpy as np
import pytest
from qtpy import QtWidgets

from pymodaq.utils.plotting.data_viewers.viewer2D_basic import Viewer2DBasic
from pymodaq.utils.plotting import scan_selector as select


def init_viewer(qtbot) -> Viewer2DBasic:
    widget = QtWidgets.QWidget()
    prog = Viewer2DBasic(widget)
    qtbot.addWidget(widget)
    widget.show()
    return prog


def test_table_model():
    assert hasattr(select, 'TableModel')
    assert hasattr(select.TableModel, 'data_as_ndarray')


class MockViewer:
    def __init__(self, title: str):
        self.title = title


def test_selector_items():
    N = 3
    for ind in range(N):
        title = f'Viewer{ind:02d}'
        item = select.SelectorItem(MockViewer(title=title))
        assert item.name == f'{title}_{ind:03d}'


class TestSelectors:
    def test_selectors_methods(self):

        selectors = [select.selector_factory.builders['SelectorFactory'].get(name)
                     for name in select.selector_factory.keys]
        selectors.append(select.SelectorWrapper)

        for selector in selectors:
            assert hasattr(selector, 'get_header')
            assert hasattr(selector, 'get_coordinates')
            assert hasattr(selector, 'set_coordinates')

    def test_selector_coordinates(self, qtbot):
        viewer2D = init_viewer(qtbot)
        scan_selector = select.ScanSelector(viewer_items=[select.SelectorItem(viewer2D, 'viewer2D')])

        for selector_name in select.selector_factory.keys:
            scan_selector.selector_type = selector_name

            assert np.all(scan_selector.selector.get_coordinates() ==
                          pytest.approx(scan_selector.settings['coordinates'].data_as_ndarray()))

            wrapper = select.SelectorWrapper(scan_selector.selector)
            assert np.all(wrapper.get_coordinates() ==
                          pytest.approx(scan_selector.settings['coordinates'].data_as_ndarray()))


class TestScanSelector:

    def test_attributes(self):
        assert hasattr(select.ScanSelector, 'selector_type')
        assert hasattr(select.ScanSelector, 'viewers_items')

    def test_usage(self, qtbot):
        viewer2D = init_viewer(qtbot)
        viewer2D_bis = init_viewer(qtbot)
        name = 'viewer2D'
        name_bis = 'viewer2D_bis'
        scan_selector = select.ScanSelector(viewer_items=[select.SelectorItem(viewer2D, name),
                                                          select.SelectorItem(viewer2D_bis, name_bis)])

        assert scan_selector.sources_names == [name, name_bis]
        assert scan_selector.source_name == name

        coordinates = np.array([[2.0, 4.5], [5.0, 25]])

        with qtbot.wait_signal(scan_selector.selector.sigRegionChangeFinished, timeout=10000) as blocker:
            scan_selector.selector.set_coordinates(coordinates)
        assert np.all(scan_selector.selector.get_coordinates() ==
                      pytest.approx(scan_selector.settings['coordinates'].data_as_ndarray()))

    def test_change_source(self, qtbot):
        viewer2D = init_viewer(qtbot)
        viewer2D_bis = init_viewer(qtbot)
        name = 'viewer2D'
        name_bis = 'viewer2D_bis'
        scan_selector = select.ScanSelector(viewer_items=[select.SelectorItem(viewer2D, name),
                                                          select.SelectorItem(viewer2D_bis, name_bis)])

        assert scan_selector.source_name == name
        scan_selector.source_name = name_bis
        assert scan_selector.source_name == name_bis

        coordinates = np.array([[2.0, 4.5], [5.0, 25]])

        with qtbot.wait_signal(scan_selector.selector.sigRegionChangeFinished, timeout=10000) as blocker:
            scan_selector.selector.set_coordinates(coordinates)
        assert np.all(scan_selector.selector.get_coordinates() ==
                      pytest.approx(scan_selector.settings['coordinates'].data_as_ndarray()))
