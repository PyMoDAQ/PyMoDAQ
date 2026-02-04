import pytest
from pyqtgraph import mkColor

from pymodaq_gui.plotting.items.roi import RoiInfo, LinearROI, RectROI
from pymodaq_gui.plotting.utils.plot_utils import Point


class TestInfoFromROI:
    def test_ini(self):
        origin = Point(23)
        width = 40
        height = 25
        with pytest.raises(TypeError):
            roi_info = RoiInfo(origin)

        roi_info = RoiInfo(origin, width)

        assert isinstance(roi_info.origin, Point)
        assert roi_info.origin == origin

    def test_create_from_linear_roi(self, qtbot):
        pos_linear = [-30, 65]
        linear_color = (34, 78, 23)
        linear_roi = LinearROI(pos=pos_linear)
        linear_roi.setPen(linear_color)
        linear_roi_info = RoiInfo.info_from_linear_roi(linear_roi)

        assert linear_roi_info.origin == Point(pos_linear[0])
        assert linear_roi_info.size[0] == pytest.approx(pos_linear[1]-pos_linear[0])
        assert linear_roi_info.color == mkColor(linear_color)
        assert len(linear_roi_info.size) == 1
        assert linear_roi_info.roi_class == LinearROI

    def test_create_from_rect_roi(self, qtbot):
        pos = [-30, 65]
        size = [78, 5]
        color = (34, 78, 23)
        roi = RectROI(pos=pos, size=size)
        roi.setPen(color)
        roi_info = RoiInfo.info_from_rect_roi(roi)

        assert roi_info.origin == Point(pos[-1::-1])
        assert len(roi_info.size) == 2
        assert roi_info.size[0] == pytest.approx(size[1])  # ROI takes argument as (x, y) while
        # roi_info refers to the index of the numpy data (line, column, ...)
        assert roi_info.color == mkColor(color)
        assert roi_info.size[1] == pytest.approx(size[0])  # ROI takes argument as (x, y) while
        # roi_info refers to the index of the numpy data (line, column, ...)
        assert roi_info.roi_class == RectROI

    def test_get_repr(self, qtbot):
        pos = [-30, 65]
        size = [78, 5]
        color = (34, 78, 23)
        roi = RectROI(pos=pos, size=size)
        roi.setPen(color)
        roi_info = RoiInfo.info_from_rect_roi(roi)

        print(roi_info)
