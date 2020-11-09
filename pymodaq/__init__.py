try:  #in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils import daq_utils as utils
    logger = utils.set_logger('pymodaq', add_handler=True, base_logger=True)
    logger.info('')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('')
except:
    print("Couldn't create the local folder to store logs , presets...")




