
import os
import sys
import warnings

from qtpy import QtCore
from qtpy.QtCore import QLocale
from pymodaq_utils import logger as logger_module
from pymodaq_utils.config import Config

from pymodaq_gui.qvariant import QVariant


logger = logger_module.set_logger(logger_module.get_module_name(__file__))

config = Config()


def decode_data(encoded_data):
    """
    Decode QbyteArrayData generated when drop items in table/tree/list view
    Parameters
    ----------
    encoded_data: QByteArray
                    Encoded data of the mime data to be dropped
    Returns
    -------
    data: list
            list of dict whose key is the QtRole in the Model, and the value a QVariant

    """
    data = []

    ds = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
    while not ds.atEnd():
        row = ds.readInt32()
        col = ds.readInt32()

        map_items = ds.readInt32()
        item = {}
        for ind in range(map_items):
            key = ds.readInt32()
            #TODO check this is fine
            value = QVariant()
            #value = None
            ds >> value
            item[QtCore.Qt.ItemDataRole(key)] = value.value()
        data.append(item)
    return data


def setLocale():
    """
    defines the Locale to use to convert numbers to strings representation using language/country conventions
    Default is English and US
    """
    language = getattr(QLocale, config('style', 'language'))
    country = getattr(QLocale, config('style', 'country'))
    QLocale.setDefault(QLocale(language, country))

