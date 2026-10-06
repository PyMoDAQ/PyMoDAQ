import warnings
warnings.filterwarnings("ignore", message=".*libpyside.*", category=RuntimeWarning)
# deactivate messages when disconnect fails (catched by TypeError for pyqt6 and pyqt5
# but pyside6 do not do errors but throw this Runtimewarning)


def deprecation_msg(message, stacklevel=3):
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


def user_warning(message, stacklevel=3):
    warnings.warn(message, UserWarning, stacklevel=stacklevel)

