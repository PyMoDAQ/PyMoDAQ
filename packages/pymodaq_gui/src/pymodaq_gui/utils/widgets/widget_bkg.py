from pathlib import Path
from typing import Union

from qtpy import QtWidgets, QtGui


class WidgetWithBkg(QtWidgets.QWidget):
    """ Widget with a png file as a background texture

    Parameters
    ----------
    bkg_path: Path
        Path to a valid png file to be used as background
    """

    def __init__(self, bkg_path: Union[str, Path], *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(bkg_path, str):
            bkg_path = Path(bkg_path)
            if not bkg_path.is_file():
                raise ValueError(f'Unknown background file with path: {bkg_path}')

        self._bkg_path = bkg_path
        self.setup_palette()

    def setup_palette(self):
        pixmap = QtGui.QPixmap(str(self._bkg_path))
        self.setFixedSize(pixmap.size())

        palette = QtGui.QPalette()
        palette.setBrush(palette.ColorRole.Window, QtGui.QBrush(pixmap))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
