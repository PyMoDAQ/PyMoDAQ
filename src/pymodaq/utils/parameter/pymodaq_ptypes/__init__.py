from pyqtgraph.parametertree.parameterTypes.basetypes import (SimpleParameter, GroupParameter,
                                                              GroupParameterItem)
from .bool import BoolPushParameter
from .pixmap import PixmapParameter, PixmapCheckParameter
from .slide import SliderSpinBox, SliderParameter
from .led import LedPushParameter, LedParameter
from .date import DateParameter, DateTimeParameter, TimeParameter
from .list import ListParameter
from .table import TableParameter
from .tableview import TableViewParameter, TableViewCustom
from .itemselect import ItemSelectParameter
from .filedir import FileDirParameter
from .text import PlainTextPbParameter
from .numeric import NumericParameter

from pyqtgraph.parametertree.Parameter import registerParameterType, registerParameterItemType, Parameter

registerParameterType('float', NumericParameter, override=True)
registerParameterType('int',   NumericParameter, override=True)
registerParameterType('bool_push', BoolPushParameter, override=True)
registerParameterType('pixmap', PixmapParameter, override=True)
registerParameterType('pixmap_check', PixmapCheckParameter, override=True)

registerParameterType('slide', SliderParameter, override=True)

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
