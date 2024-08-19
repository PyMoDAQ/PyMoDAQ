from qtpy import API_NAME

if API_NAME.lower() == 'pyqt5':
    from qtpy.QtCore import QVariant
else:
    def QVariant(*args):
        if len(args) > 1:
            raise TypeError('Argument of QVariant is a singlet')
        elif len(args) == 1:
            return args[0]
        else:
            return None