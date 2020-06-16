try:  #in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils import daq_utils as utils
    logger = utils.set_logger('pymodaq', True, True)
except:
    print("Couldn't create the local folder to store logs , presets...")




