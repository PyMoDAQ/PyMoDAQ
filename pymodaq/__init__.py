try:
    from .daq_utils import daq_utils as utils
    logger = utils.set_logger(utils.get_module_name(__file__), True, True)
except:
    print("Couldn't create the local folder to store logs , presets...")



