from pymodaq_utils.warnings import deprecation_msg

from pymodaq.utils.custom_ext import CustomExt  # noqa

deprecation_msg('Importing CustomExt from pymodaq.extension.custom_ext is deprecated, '
                'please use pymodaq.utils.custom_ext')