
try:
    from pymodaq_utils.logger import set_logger
    from pymodaq_utils.utils import get_version, PackageNotFoundError
    try:
        __version__ = get_version('pymodaq_utils')
    except PackageNotFoundError:
        __version__ = '0.0.0dev'
    try:
        logger_var = set_logger('pymodaq', add_handler=True, base_logger=True)
        logger_var.info('')
        logger_var.info('')
        logger_var.info('************************')
        logger_var.info(f"Registering Serializables...")
        from pymodaq_utils.serialize.serializer import SerializableFactory, SERIALIZABLE
        logger_var.info(f"Done")
        logger_var.info('************************')
    except Exception:
        print("Couldn't create the local folder to store logs , presets...")

    from pymodaq_utils.config import Config

    CONFIG = Config()  # to ckeck for config file existence, otherwise create one


except Exception as e:
    try:
        logger_var.exception(str(e))
    except Exception as e:
        print(str(e))
