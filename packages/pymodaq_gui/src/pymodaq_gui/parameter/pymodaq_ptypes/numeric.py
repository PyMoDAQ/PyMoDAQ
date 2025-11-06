from pyqtgraph.parametertree.parameterTypes.basetypes import SimpleParameter
from pyqtgraph.parametertree.parameterTypes.numeric import NumericParameterItem


class NumericParameter(SimpleParameter):
    itemClass = NumericParameterItem

    def __init__(self, **opts):
        super().__init__(**opts)

    def setLimits(self, limits):
        curVal = self.value()
        if curVal > limits[1]:
            self.setValue(limits[1])
        elif curVal < limits[0]:
            self.setValue(limits[0])
        super().setLimits(limits)
        return limits