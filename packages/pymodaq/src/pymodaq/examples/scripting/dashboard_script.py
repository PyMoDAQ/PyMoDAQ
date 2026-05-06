from pymodaq.scripting import Detector, Actuator, Dashboard

# Once a dashboard is started:
dashboard = Dashboard()


print(dashboard.get_experiments().result())
# >>> ['default']
# Could make it so that it returns a future that completes when it's finished loading
dashboard.apply_experiment('default')

print(dashboard.get_configurations().result())
# >>> ['default', 'my_custom_config']

# Same remark as dashboard.apply_preset
dashboard.apply_configuration('default')

print(dashboard.get_devices().result())  # returns the names
# >>> {'actuators': ['Theta', 'Temperature', 'Power', 'Xaxis'], 'detectors': ['Det2D', 'Det0D', 'Det1D']}

devices = dashboard.get_scripting_devices()
print(devices)
# >>>  {'actuators': {'Theta': <Actuator object>, 'Temperature': <Actuator object>, 'Power': <Actuator object>, 'Xaxis': <Actuator object>}, 'detectors': {'Det2D': <Detector object>, 'Det0D': <Detector object>, 'Det1D': <Detector object>}}


#Then each device can be used
devices['actuators']['Angle'].move_abs('90°')