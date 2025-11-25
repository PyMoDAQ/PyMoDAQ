import warnings


def deprecation_msg(message, stacklevel=2):
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


def user_warning(message, stacklevel=3):
    warnings.warn(message, UserWarning, stacklevel=stacklevel)

