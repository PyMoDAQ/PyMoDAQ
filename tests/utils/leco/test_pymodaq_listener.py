from pyleco.core.data_message import DataMessage
from pyleco.test import FakeCommunicator
import pytest

from pymodaq.utils.leco.pymodaq_listener import PymodaqListener
from pymodaq.utils.daq_utils import ThreadCommand


@pytest.fixture
def listener() -> PymodaqListener:
    listener = PymodaqListener(name="listener")#, context=FakeContext())  # type: ignore
    listener.communicator = FakeCommunicator(name="listener")  # type: ignore[assign]
    return listener


@pytest.mark.parametrize(
    "tc, message",
    (
        (
            ThreadCommand("command", [8]),
            DataMessage.from_frames(
                b"listener",
                b"",
                b'{"type":"ThreadCommand","command":"command","attribute":[8]}',
            ),
        ),
        (
            ThreadCommand("command", [1 + 2j]),
            DataMessage.from_frames(
                b"listener",
                b"",
                b'{"type":"ThreadCommand","command":"command","attribute":[null],"binary":[0]}',
                b"\x00\x00\x00\x06scalar\x00\x00\x00\x04<c16\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@",
            ),
        ),
    ),
)
def test_create_thread_command_message(
    listener: PymodaqListener, tc: ThreadCommand, message: DataMessage
):
    m = listener.create_thread_command_message(tc)
    assert m.topic == message.topic
    print(m.payload[0])
    assert m.data == message.data
    assert m.payload[1:] == message.payload[1:]



@pytest.mark.parametrize(
    "payload, message",
    (
        (
            7,
            DataMessage(
                "listener", data={"type": "Signal", "name": "signal", "content": 7}
            ),
        ),
        (
            1 + 2j,
            DataMessage.from_frames(
                b"listener",
                b"",
                b'{"type": "Signal", "name": "signal", "content": null}',
                b"\x00\x00\x00\x06scalar\x00\x00\x00\x04<c16\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@",
            ),
        ),
    ),
)
def test_abc(listener: PymodaqListener, payload, message: DataMessage):
    m = listener.create_signal_message("signal", signal_payload=payload)
    assert m.topic == message.topic
    assert m.data == message.data
    assert m.payload[1:] == message.payload[1:]
