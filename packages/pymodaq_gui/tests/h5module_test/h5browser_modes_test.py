from pathlib import Path
from unittest import mock

import numpy as np
import pytest

from pymodaq_data.data import Axis, DataRaw, DataToExport
from pymodaq_data.h5modules.data_saving import DataToExportSaver
from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq_gui.h5modules import browsing
from qtpy import QtWidgets


@pytest.fixture
def h5_path(tmp_path):
    dte = DataToExport('test')
    for name, concept in (('background', 'DarkSpectrum'), ('signal', 'SampleSpectrum')):
        data = DataRaw(name, data=[np.random.rand(10)], units='counts', labels=[name],
                       axes=[Axis('x', data=np.arange(10.), index=0)])
        data.add_extra_attribute(semantic_iri='https://x.org/spectro#' + concept,
                                 quantity_kind='qk:Count', unit_iri='unit:NUM')
        dte.append(data)
    h5 = H5SaverLowLevel()
    path = tmp_path / 'file.h5'
    h5.init_file(file_name=path, new_file=True)
    DataToExportSaver(h5).add_data(h5.get_set_group(h5.raw_group, 'Det'), dte)
    h5.close_file()
    return path


def test_modes_show_same_data(qtbot, h5_path):
    with mock.patch.object(browsing.H5Browser, 'check_version'):
        window = QtWidgets.QMainWindow()
        browser = browsing.H5Browser(window, h5file_path=h5_path)
    qtbot.addWidget(window)
    shown = []
    browser.hyper_viewer.show_data = lambda data, **kwargs: shown.append(data)
    tree = browser.view.h5file_tree.tree

    def leaves():
        stack, found = [tree.topLevelItem(0)], []
        while stack:
            item = stack.pop()
            stack += [item.child(i) for i in range(item.childCount())]
            if item.text(2).endswith('Data00'):
                found.append(item)
        return found

    assert [browser.view.mode_combo.itemData(i) for i in range(browser.view.mode_combo.count())] == \
        ['hdf5', 'concept', 'quantity']

    for mode in ('hdf5', 'concept', 'quantity'):
        browser.set_mode(mode)
        assert len(leaves()) == 2
        shown.clear()
        for leaf in leaves():
            tree.setCurrentItem(leaf)
            browser.show_h5_data(leaf)
        assert sorted(d.name for d in shown) == ['background', 'signal']

    # an item that is only a grouping label (a concept) does nothing on double-click
    browser.set_mode('concept')
    shown.clear()
    tree.setCurrentItem(tree.topLevelItem(0).child(0))
    browser.show_h5_data(tree.currentItem())
    assert shown == []
