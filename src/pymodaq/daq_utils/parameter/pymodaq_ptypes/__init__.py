from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter, GroupParameter, GroupParameterItem

from .pixmap import PixmapParameterItem, PixmapCheckParameterItem
from .slide import SliderSpinBox, SliderParameterItem
from .led import LedPushParameter, LedParameter
from .date import DateParameter, DateTimeParameter, TimeParameter
from .list import ListParameter
from .table import TableParameter
from .tableview import TableViewParameter
from .itemselect import ItemSelectParameter

from pyqtgraph.parametertree.Parameter import registerParameterType, registerParameterItemType


registerParameterItemType('pixmap', PixmapParameterItem, SimpleParameter, override=True)
registerParameterItemType('pixmap_check', PixmapCheckParameterItem, SimpleParameter, override=True)
registerParameterItemType('slide', SliderParameterItem, SimpleParameter, override=True)

registerParameterType('led', LedParameter, override=True)
registerParameterType('led_push', LedPushParameter, override=True)
registerParameterType('date', DateParameter, override=True)
registerParameterType('date_time', DateParameter, override=True)
registerParameterType('time', DateParameter, override=True)

registerParameterType('list', ListParameter, override=True)
registerParameterType('table', TableParameter, override=True)

registerParameterType('table_view', TableViewParameter, override=True)
registerParameterType('itemselect', ItemSelectParameter, override=True)
