from pymodaq_utils.logger import set_logger
from pymodaq_utils.config import Config

logger = set_logger('pymodaq')
config = Config()  # to ckeck for config file existence, otherwise create one


if config('network', 'leco-server', 'run_coordinator_at_startup'):
    try:
        from pymodaq.utils.leco.utils import start_coordinator

        logger.info('')
        logger.info('')
        logger.info(f'********************************')
        logger.info(f"Starting the LECO Coordinator...")
        start_coordinator()
        logger.info(f"Done")
    except ImportError as e:
        logger.warning(f'Issue while importing the pyleco package: {str(e)}')
    except Exception as e:
        logger.warning(f'Issue while starting the pyleco coordinator: {str(e)}')
    finally:
        logger.info('************************')
        logger.info('')
        logger.info('')