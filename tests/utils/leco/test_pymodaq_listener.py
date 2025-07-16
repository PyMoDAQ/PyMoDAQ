
from pyleco.core.message import Message, MessageTypes
from pyleco.json_utils.json_objects import ErrorResponse, ResultResponse, Request
from pyleco.json_utils.errors import RECEIVER_UNKNOWN, NODE_UNKNOWN
from pyleco.test import FakeCommunicator
import pytest
from pymodaq.utils.leco.pymodaq_listener import ActorListener


name = "listener"

@pytest.fixture
def actorListener() -> ActorListener:
    listener = ActorListener(name=name)  # , context=FakeContext())  # type: ignore
    listener.communicator = FakeCommunicator(name=name)  # type: ignore[assign]
    return listener



class TestSendRPCToRemote:
    remote_name = "receiver"

    def test_send_message_successfully(self, actorListener: ActorListener):
        actorListener.set_remote_name(self.remote_name)
        actorListener.communicator._r = [  # type: ignore[assign]
            Message(
                name,
                self.remote_name,
                message_type=MessageTypes.JSON,
                data=ResultResponse(1, None),
            )
        ]
        actorListener.send_rpc_message_to_remote("whatever")
        sent: Message = actorListener.communicator._s[0]  # type: ignore
        expected_sent = Message(
            self.remote_name,
            name,
            data=Request(1, "whatever"),
            header=sent.header,
        )
        assert expected_sent == sent
        assert self.remote_name in actorListener.remote_names

    @pytest.mark.parametrize("error", (RECEIVER_UNKNOWN, NODE_UNKNOWN))
    def test_unreachable_receiver_removes_receiver(self, actorListener: ActorListener, error):
        actorListener.set_remote_name(self.remote_name)
        actorListener.communicator._r = [  # type: ignore[assign]
            Message(
                name,
                self.remote_name,
                message_type=MessageTypes.JSON,
                data=ErrorResponse(None, error=error),
            )
        ]
        actorListener.send_rpc_message_to_remote("whatever")
        assert self.remote_name not in actorListener.remote_names


