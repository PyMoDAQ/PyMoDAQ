import sys, yaml
from PyQt5.QtCore import QCoreApplication, QTimer, pyqtRemoveInputHook
from pymodaq_gui.state_machine.statemachine import StateMachine
from pymodaq_gui.state_machine.factory import StateMachineFactory
from sequencer import Sequencer, ActuatorController
from dummy_devices import DummyDataProcessor, DummyCamera, DummyActuator, \
    DummyShutter, DummyDelayLine, DummyScanner1D

with open('step-scan.yml', 'rt') as yaml_file:
    yaml_data = yaml.load(yaml_file, Loader=yaml.SafeLoader)

## start-up
app = QCoreApplication(sys.argv)
pyqtRemoveInputHook() # enable using pdb inside qt event loop

## dashboard business
camera = DummyCamera()
signal_shutter = DummyShutter("excitation-shutter")
reference_shutter = DummyShutter("reference-shutter")
delay_line = DummyDelayLine("delay")

## sequencer extension
data_processor = DummyDataProcessor() # specific to this test sequencer test
state_machine = StateMachineFactory.from_yaml(yaml_data)
# actuator assignment dict would be made by gui of the sequencer extension
# need for ActuatorController -> c.f. its definition in sequencer.py
actuator_controller = \
    ActuatorController(actuators={'excitation-shutter': signal_shutter,
                                  'reference-shutter': reference_shutter,
                                  'delay': delay_line})
# scanner chosen on gui / in yaml file / coded into specific sequencer
# whatever will be best
scanner = DummyScanner1D(actuator_controller, 'delay', 10)
# assignment by combination of yaml content and gui choice
sequencer = \
    Sequencer(yaml_data['states'], actuator_controller,
              detectors={'camera': camera},
              data_processors={'data': data_processor},
              scanners={'loop': scanner})

# other needed connections
scanner.done.connect(lambda: state_machine.take_event('scan-done'))
actuator_controller.devices_ready.connect(lambda: state_machine\
                                          .take_event('devices-ready'))

camera.data_ready.connect(data_processor.take_data)
data_processor.acquisition_done.connect(lambda: state_machine\
                                        .take_event('acquisition-done'))

# run

def watchdog_quit():
    print("watchdog: woof-woof, quitting")
    app.quit()

state_machine.state_entered.connect(sequencer.event)
state_machine.finished.connect(app.quit)
state_machine.start()
QTimer.singleShot(3000, watchdog_quit)
sys.exit(app.exec())
