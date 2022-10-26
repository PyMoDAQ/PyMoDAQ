import importlib.util
import os
import sys
from pint import UnitRegistry
from pathlib import Path

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

try:
    with open(str(Path(__file__).parent.joinpath('resources/VERSION')), 'r') as fvers:
        __version__ = fvers.read().strip()

    # in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils.daq_utils import set_logger, copy_preset, setLocale, set_qt_backend
    from pymodaq.utils.config import Config

    try:
        logger = set_logger('pymodaq', add_handler=True, base_logger=True)
    except Exception:
        print("Couldn't create the local folder to store logs , presets...")

    # issue on windows when using .NET code within multithreads, this below allows it but requires the
    # pywin32 (pythoncom) package
    if importlib.util.find_spec('clr') is not None:
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ModuleNotFoundError as e:
            infos = "You have installed plugins requiring the pywin32 package to work correctly," \
                    " please type in *pip install pywin32* and restart PyMoDAQ"
            print(infos)
            logger.warning(infos)

    config = Config()  # to ckeck for config file existence, otherwise create one
    copy_preset()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Setting Qt backend to: {config['qtbackend']['backend']} ...")
    logger.info('************************')
    set_qt_backend()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Setting Locale to {config['style']['language']} / {config['style']['country']}")
    logger.info('************************')
    setLocale()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Initializing the pint unit register')
    logger.info('************************')
    ureg = UnitRegistry()
    Q_ = ureg.Quantity
    logger.info('')
    logger.info('')

except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))

import sys
from importlib import import_module
sys.modules['pymodaq.daq_utils'] = import_module('.utils', 'pymodaq')
sys.modules['pymodaq.daq_utils.abstract.logger'] = import_module('.abstract.logger', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.array_manipulation'] = import_module('.array_manipulation', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.calibration_camera'] = import_module('.calibration_camera', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.chrono_timer'] = import_module('.chrono_timer', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.config'] = import_module('.config', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.conftests'] = import_module('.conftests', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.custom_parameter_tree'] = import_module('.custom_parameter_tree', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.daq_enums'] = import_module('.daq_enums', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.daq_utils'] = import_module('.daq_utils', 'pymodaq.utils')
try:
    import sqlalchemy
    sys.modules['pymodaq.daq_utils.db.db_logger.db_logger'] = import_module('.db.db_logger.db_logger', 'pymodaq.utils')
    sys.modules['pymodaq.daq_utils.db.db_logger.db_logger_models'] = import_module('.db.db_logger.db_logger_models', 'pymodaq.utils')
except ModuleNotFoundError:
    pass
sys.modules['pymodaq.daq_utils.exceptions'] = import_module('.exceptions', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.custom_app'] = import_module('.gui_utils.custom_app', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.dock'] = import_module('.gui_utils.dock', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.file_io'] = import_module('.gui_utils.file_io', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.layout'] = import_module('.gui_utils.layout', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.list_picker'] = import_module('.gui_utils.list_picker', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.utils'] = import_module('.gui_utils.utils', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.label'] = import_module('.gui_utils.widgets.label', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.lcd'] = import_module('.gui_utils.widgets.lcd', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.push'] = import_module('.gui_utils.widgets.push', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.qled'] = import_module('.gui_utils.widgets.qled', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.spinbox'] = import_module('.gui_utils.widgets.spinbox', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.gui_utils.widgets.table'] = import_module('.gui_utils.widgets.table', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.h5modules'] = import_module('.h5modules', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.action_manager'] = import_module('.managers.action_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.batchscan_manager'] = import_module('.managers.batchscan_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.modules_manager'] = import_module('.managers.modules_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.overshoot_manager'] = import_module('.managers.overshoot_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.parameter_manager'] = import_module('.managers.parameter_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.preset_manager'] = import_module('.managers.preset_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.preset_manager_utils'] = import_module('.managers.preset_manager_utils', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.remote_manager'] = import_module('.managers.remote_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.managers.roi_manager'] = import_module('.managers.roi_manager', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.math_utils'] = import_module('.math_utils', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.messenger'] = import_module('.messenger', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.ioxml'] = import_module('.parameter.ioxml', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.bool'] = import_module('.parameter.pymodaq_ptypes.bool', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.date'] = import_module('.parameter.pymodaq_ptypes.date', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.filedir'] = import_module('.parameter.pymodaq_ptypes.filedir', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.itemselect'] = import_module('.parameter.pymodaq_ptypes.itemselect', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.led'] = import_module('.parameter.pymodaq_ptypes.led', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.list'] = import_module('.parameter.pymodaq_ptypes.list', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.numeric'] = import_module('.parameter.pymodaq_ptypes.numeric', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.pixmap'] = import_module('.parameter.pymodaq_ptypes.pixmap', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.slide'] = import_module('.parameter.pymodaq_ptypes.slide', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.table'] = import_module('.parameter.pymodaq_ptypes.table', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.tableview'] = import_module('.parameter.pymodaq_ptypes.tableview', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.pymodaq_ptypes.text'] = import_module('.parameter.pymodaq_ptypes.text', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.parameter.utils'] = import_module('.parameter.utils', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer0D'] = import_module('.plotting.data_viewers.viewer0D', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer0D_GUI'] = import_module('.plotting.data_viewers.viewer0D_GUI', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer1D'] = import_module('.plotting.data_viewers.viewer1D', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer1Dbasic'] = import_module('.plotting.data_viewers.viewer1Dbasic', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer2D'] = import_module('.plotting.data_viewers.viewer2D', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewer2D_basic'] = import_module('.plotting.data_viewers.viewer2D_basic', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewerbase'] = import_module('.plotting.data_viewers.viewerbase', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.data_viewers.viewerND'] = import_module('.plotting.data_viewers.viewerND', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.image_viewer'] = import_module('.plotting.image_viewer', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.items.axis_scaled'] = import_module('.plotting.items.axis_scaled', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.items.crosshair'] = import_module('.plotting.items.crosshair', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.items.image'] = import_module('.plotting.items.image', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.navigator'] = import_module('.plotting.navigator', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.scan_selector'] = import_module('.plotting.scan_selector', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.utils.filter'] = import_module('.plotting.utils.filter', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.utils.plot_utils'] = import_module('.plotting.utils.plot_utils', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.utils.signalND'] = import_module('.plotting.utils.signalND', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewer0D.viewer0D_main'] = import_module('.plotting.viewer0D.viewer0D_main', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic'] = import_module('.plotting.viewer1D.viewer1Dbasic', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewer1D.viewer1D_main'] = import_module('.plotting.viewer1D.viewer1D_main', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewer2D.viewer_2D_basic'] = import_module('.plotting.viewer2D.viewer_2D_basic', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewer2D.viewer_2D_main'] = import_module('.plotting.viewer2D.viewer_2D_main', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.plotting.viewerND.viewerND_main'] = import_module('.plotting.viewerND.viewerND_main', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.qvariant'] = import_module('.qvariant', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.scanner'] = import_module('.scanner', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.tcp_server_client'] = import_module('.tcp_server_client', 'pymodaq.utils')
sys.modules['pymodaq.daq_utils.tree_layout.tree_layout_main'] = import_module('.tree_layout.tree_layout_main', 'pymodaq.utils')
