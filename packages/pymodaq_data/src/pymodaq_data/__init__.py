import importlib.util
import os
import sys
from pint import UnitRegistry

try:
    from pymodaq_utils.logger import set_logger
    from pymodaq_utils.utils import get_version, PackageNotFoundError
    try:
        __version__ = get_version('pymodaq_data')
    except PackageNotFoundError:
        __version__ = '0.0.0dev'
    try:
        logger = set_logger('pymodaq_data', add_handler=True, base_logger=True)
    except Exception:
        print("Couldn't create the local folder to store logs , presets...")

    logger.info('************************')
    logger.info('Initializing the pint unit register')
    logger.info('************************')
    ureg = UnitRegistry()
    ureg.default_format = '~'
    Q_ = ureg.Quantity
    Unit = ureg.Unit
    logger.info('')
    logger.info('')

    from pymodaq_data.h5modules.utils import register_exporters
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Registering exporters...")
    register_exporters()
    logger.info(f"Done")
    logger.info('************************')

    from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Registering plotters...")
    register_plotter()
    logger.info(f"Done")
    logger.info('************************')


    from pymodaq_data.data import (DataRaw, DataWithAxes, DataToExport, Axis,
                                   DataCalculated, DataDim, DataDistribution, DataSource, DataBase)

except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))
