from pymodaq_utils.logger import set_logger, get_module_name, get_set_config_dir, get_base_logger

from pymodaq_utils.warnings import deprecation_msg

deprecation_msg('Importing logger stuff from pymodaq is deprecated in pymodaq>5.0.0,'
                'please use the pymodaq_utils package')
