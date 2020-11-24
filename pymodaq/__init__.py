try:
    # in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils.daq_utils import set_logger, load_config
    logger = set_logger('pymodaq', add_handler=True, base_logger=True)
    config = load_config()  # to ckeck for config file existence, otherwise create one
    logger.info('')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('')

except Exception as e:
    try:
        logger.exception(str(e))
        print("Couldn't create the local folder to store logs , presets...")
    except Exception as e:
        print("Couldn't create the local folder to store logs , presets...")
