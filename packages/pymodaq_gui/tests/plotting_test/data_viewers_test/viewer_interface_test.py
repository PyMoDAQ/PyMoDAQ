# import pytest
# import inspect
# from qtpy import QtWidgets
# from qtpy.QtCore import QObject
#
# from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
# from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
# from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
#
# @pytest.fixture
# def ini_qt_widget(qtbot):
#     widget = QtWidgets.QWidget()
#     qtbot.addWidget(widget)
#     widget.show()
#     yield qtbot, widget
#     widget.close()
#
#
# @pytest.mark.parametrize("viewer_class, expected", [
#     (Viewer0D, {
#         "show_data": True,
#         "roi_manager": False,
#         "ROI_changed": True,
#     }),
#     (Viewer1D, {
#         "show_data": True,
#         "roi_manager": True,
#         "ROI_changed": True,
#     }),
#     (Viewer2D, {
#         "show_data": True,
#         "roi_manager": True,
#         "ROI_changed": True,
#     }),
# ])
# def test_viewer_interface_consistency(ini_qt_widget, viewer_class, expected):
#     qtbot, widget = ini_qt_widget
#     viewer = viewer_class(widget)
#
#
#     for attribute, should_exist in expected.items():
#         if should_exist:
#             assert hasattr(viewer, attribute)
#             if attribute == "sig_roi_changed":
#                 signal = getattr(viewer, attribute)
#                 assert isinstance(signal, QObject)
#         else:
#             assert not hasattr(viewer, attribute)
#
#
#
# def test_sig_roi_changed_argument_and_connection(ini_qt_widget):
#     qtbot, widget = ini_qt_widget
#     viewer = Viewer2D(widget)
#     viewer.roi_manager.add_ROI(0, 'roi1')
#
#     called_args = []
#     def test_slot(*args):
#         called_args.append(args)
#
#     viewer.roi_manager.sig_roi_changed.connect(test_slot)
#     viewer.roi_manager.ROIs['roi1'].setPos((15, 15))
#
#     qtbot.waitUntil(lambda: len(called_args) > 0, timeout=1000)
#     assert isinstance(called_args[0][0], str)
#
#
# #TODO with real signal/slot signature
# def test_slot_signature_matches_expected():
#     def on_roi_changed(self, roi_name: str): pass
#     sig = inspect.signature(on_roi_changed)
#     params = list(sig.parameters.values())
#     assert len(params) == 2
#     assert params[1].annotation in [str, inspect._empty]