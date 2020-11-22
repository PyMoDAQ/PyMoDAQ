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

params = [
    {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True, 'children': [
        {'title': 'Models class:', 'name': 'model_class', 'type': 'list', 'values': models},
        {'title': 'Modules managers:', 'name': 'module_settings',
         'tooltip': 'Get/Set managers settings for each module in the current model', 'type': 'bool', 'value': False},
        {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},
    ]},
    {'title': 'Move settings:', 'name': 'move_settings', 'expanded': True, 'type': 'group', 'visible': False,
     'children': [
         {'title': 'Units:', 'name': 'units', 'type': 'str', 'value': ''}]},
    # here only to be compatible with DAQ_Scan, the model could update it

    {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': True, 'type': 'group', 'children': [
        {'title': 'Acquisition Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000},
        {'name': 'epsilon', 'type': 'float', 'value': 0.01, 'tooltip': 'Precision at which move is considered as done'},
        {'title': 'PID controls:', 'name': 'pid_controls', 'type': 'group', 'children': [
            {'title': 'Set Point:', 'name': 'set_point', 'type': 'float', 'value': 0., ',readonly': True},
            {'title': 'Sample time (ms):', 'name': 'sample_time', 'type': 'int', 'value': 10},
            {'title': 'Refresh plot time (ms):', 'name': 'refresh_plot_time', 'type': 'int', 'value': 200},
            {'title': 'Output limits:', 'name': 'output_limits', 'expanded': True, 'type': 'group', 'children': [
                {'title': 'Output limit (min):', 'name': 'output_limit_min_enabled', 'type': 'bool', 'value': False},
                {'title': 'Output limit (min):', 'name': 'output_limit_min', 'type': 'float', 'value': 0},
                {'title': 'Output limit (max):', 'name': 'output_limit_max_enabled', 'type': 'bool', 'value': False},
                {'title': 'Output limit (max:', 'name': 'output_limit_max', 'type': 'float', 'value': 100},
            ]},
            {'title': 'Filter:', 'name': 'filter', 'expanded': True, 'type': 'group', 'children': [
                {'title': 'Enable filter:', 'name': 'filter_enable', 'type': 'bool', 'value': False},
                {'title': 'Filter step:', 'name': 'filter_step', 'type': 'float', 'value': 0, 'min': 0},
            ]},
            {'title': 'Auto mode:', 'name': 'auto_mode', 'type': 'bool', 'value': False, 'readonly': True},
            {'title': 'Prop. on measurement:', 'name': 'proportional_on_measurement', 'type': 'bool', 'value': False},
            {'title': 'PID constants:', 'name': 'pid_constants', 'type': 'group', 'children': [
                {'title': 'Kp:', 'name': 'kp', 'type': 'float', 'value': 5, 'min': 0},
                {'title': 'Ki:', 'name': 'ki', 'type': 'float', 'value': 0.01, 'min': 0},
                {'title': 'Kd:', 'name': 'kd', 'type': 'float', 'value': 0.001, 'min': 0},
            ]},

        ]},

    ]},
]
