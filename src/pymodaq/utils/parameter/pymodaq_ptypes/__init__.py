from pyqtgraph.parametertree.parameterTypes.basetypes import SimpleParameter, GroupParameter, GroupParameterItem
from .bool import BoolPushParameterItem
from .pixmap import PixmapParameterItem, PixmapCheckParameterItem
from .slide import SliderSpinBox, SliderParameterItem
from .led import LedPushParameter, LedParameter
from .date import DateParameter, DateTimeParameter, TimeParameter
from .list import ListParameter
from .table import TableParameter
from .tableview import TableViewParameter, TableViewCustom
from .itemselect import ItemSelectParameter
from .filedir import FileDirParameter
from .text import PlainTextPbParameter
from .numeric import NumericParameter

from pyqtgraph.parametertree.Parameter import registerParameterType, registerParameterItemType

registerParameterType('float', NumericParameter, override=True)
registerParameterType('int',   NumericParameter, override=True)
registerParameterItemType('bool_push', BoolPushParameterItem, SimpleParameter, override=True)
registerParameterItemType('pixmap', PixmapParameterItem, SimpleParameter, override=True)
registerParameterItemType('pixmap_check', PixmapCheckParameterItem, SimpleParameter, override=True)
registerParameterItemType('slide', SliderParameterItem, SimpleParameter, override=True)

registerParameterType('led', LedParameter, override=True)
registerParameterType('led_push', LedPushParameter, override=True)
registerParameterType('date', DateParameter, override=True)
registerParameterType('date_time', DateTimeParameter, override=True)
registerParameterType('time', TimeParameter, override=True)

registerParameterType('list', ListParameter, override=True)
registerParameterType('table', TableParameter, override=True)

registerParameterType('table_view', TableViewParameter, override=True)
registerParameterType('itemselect', ItemSelectParameter, override=True)
registerParameterType('browsepath', FileDirParameter, override=True)
registerParameterType('text_pb', PlainTextPbParameter, override=True)
