from pymodaq_gui.h5modules.h5browser import main, H5Browser  #backcompat
from pymodaq_utils.utils import deprecation_msg


deprecation_msg('H5Browser should now be loaded from the pymodaq_gui.h5modules.h5browser module')


if __name__ == '__main__':
    main()
