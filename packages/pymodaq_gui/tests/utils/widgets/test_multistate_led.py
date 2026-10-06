import pytest

from pymodaq_gui.utils.widgets.multistate_led import MultistateLED, LedState, DEFAULT_STATES
from pymodaq_gui.utils.status_palette import StatusPalette, Status


class TestLedState:
    """LedState / Status are StrEnum: members must stay interchangeable with plain strings."""

    def test_led_state_equals_plain_strings(self):
        assert LedState.FALSE == 'False'
        assert LedState.TRUE == 'True'
        assert [n for n, _ in DEFAULT_STATES] == ['False', 'True']

    def test_status_equals_plain_strings(self):
        assert list(Status) == ['off', 'idle', 'running', 'warning', 'error', 'critical']


class TestMultistateLEDEnumInterop:

    def test_set_get_state_mix_enum_and_string(self, qapp):
        led = MultistateLED()
        assert led.get_state() == 'False'
        led.set_state(LedState.TRUE)
        assert led.get_state() == 'True'
        led.set_state('false')
        assert led.get_state() == LedState.FALSE

    def test_invalid_state_still_raises(self, qapp):
        led = MultistateLED()
        with pytest.raises(ValueError):
            led.set_state('not_a_state')

    def test_status_palette_states_drive_led(self, qapp):
        led = MultistateLED(states=StatusPalette.subset(Status.OFF, Status.IDLE, Status.ERROR))
        assert led.state_names() == ['off', 'idle', 'error']
        led.set_state(Status.IDLE)
        assert led.get_state() == 'idle'
