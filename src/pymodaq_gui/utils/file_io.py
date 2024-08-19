from pathlib import Path

from pymodaq_utils.config import Config
from qtpy import QtWidgets

config = Config()


def select_file_filter(start_path=config('data_saving', 'h5file', 'save_path'), save=True, ext=None,
                       filter=None, force_save_extension=False):
    """Opens a selection file popup for loading or saving a file

    Parameters
    ----------
    start_path: str or Path
        The strating point in the file/folder system to open the popup from
    save: bool
        if True, ask you to enter a filename (with or without extension)
    ext: str
        the extension string, e.g. xml, h5, png ...
    filter: list of string
        list of possible extensions, mostly valid for loading
    force_save_extension: bool
        if True force the extension of the saved file to be set to ext

    Returns
    -------
    Path: the Path object of the file to save or load
    str: the selected filter
    """
    if ext is None:
        ext = '.h5'

    if filter is None:
        if not save:
            if not isinstance(ext, list):
                ext = [ext]
            filter = "Data files ("
            for ext_tmp in ext:
                filter += '*.' + ext_tmp + " "
            filter += ")"

    if start_path is not None:
        if not isinstance(start_path, str):
            start_path = str(start_path)
    if save:
        fname, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            None, 'Enter a file name', start_path, filter)
    else:
        fname, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            None, 'Select a file name', start_path, filter)

    if fname != '':  # execute if the user didn't cancel the file selection
        fname = Path(fname)
        if save and force_save_extension:
            parent = fname.parent
            filename = fname.stem
            fname = parent.joinpath(filename + "." + ext)  # forcing the right extension on the filename
    return fname, selected_filter


def select_file(start_path=config('data_saving', 'h5file', 'save_path'), save=True, ext=None,
                filter=None,
                force_save_extension=False):
    """Opens a selection file popup for loading or saving a file

    Parameters
    ----------
    start_path: str or Path
        The strating point in the file/folder system to open the popup from
    save: bool
        if True, ask you to enter a filename (with or without extension)
    ext: str
        the extension string, e.g. xml, h5, png ...
    filter: string
        list of possible extensions, if you need several you can separate them by ;;
        for example: "Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)"
    force_save_extension: bool
        if True force the extension of the saved file to be set to ext

    Returns
    -------
    Path: the Path object of the file to save or load
    """
    fname, selected_filter = select_file_filter(start_path, save, ext, filter,
                                                force_save_extension)
    return fname  # fname is a Path object


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    file = select_file(save=True, filter="Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)")
    print(file)
    sys.exit(app.exec_())
