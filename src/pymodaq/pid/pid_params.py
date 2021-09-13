import importlib
import os

models = []
try:
    model_mod = importlib.import_module('pymodaq_pid_models')
    for ind_file, entry in enumerate(os.scandir(os.path.join(model_mod.__path__[0], 'models'))):
        if not entry.is_dir() and entry.name != '__init__.py':
            try:
                file, ext = os.path.splitext(entry.name)
                importlib.import_module('.' + file, model_mod.__name__ + '.models')

                models.append(file)
            except Exception as e:
                print(e)
    if 'PIDModelMock' in models:
        mods = models
        mods.pop(models.index('PIDModelMock'))
        models = ['PIDModelMock']
        models.extend(mods)

except Exception as e:
    print(e)

if len(models) == 0:
    print('No valid installed models to run the pid controller')

