from pyleco.core.message import Message, MessageTypes
from pyleco.json_utils.json_objects import Request, ResultResponse, ErrorResponse
from pyleco.json_utils.errors import RECEIVER_UNKNOWN
from pyleco.test import FakeCommunicator
from pymodaq.control_modules.thread_commands import ThreadStatus
from pymodaq_utils.utils import ThreadCommand
import pytest

from pymodaq.utils.leco.leco_director import LECODirector, GenericDirector


actor_name = "actor"
director_name = "director"


class Test_check_actor_connection:
    class FakeDirector:
        def __init__(self):
            self.communicator = FakeCommunicator(director_name)
            self.controller = GenericDirector(actor=actor_name, communicator=self.communicator)
            self._status = None

        def emit_status(self, status: ThreadCommand) -> None:
            self._status = status

        check_actor_connection = LECODirector.check_actor_connection

    @pytest.fixture
    def director(self) -> LECODirector:
        dir = self.FakeDirector()
        return dir  # type: ignore

    def test_send_request(self, director: FakeDirector):
        director.communicator._r = [
            Message(
                director_name, actor_name, ResultResponse(1, None), message_type=MessageTypes.JSON
            )
        ]
        director.check_actor_connection()
        sent = director.communicator._s.pop()
        assert not director.communicator._s
        expected = Message(
            actor_name,
            director_name,
            Request(1, "pong"),
            conversation_id=sent.conversation_id,
            message_type=MessageTypes.JSON,
        )
        assert sent == expected
        assert director._status is None

    def test_not_found_error_disables_connection(self, director: FakeDirector):
        director.communicator._r = [
            Message(
                director_name,
                "COORDINATOR",
                ErrorResponse(1, RECEIVER_UNKNOWN),
                message_type=MessageTypes.JSON,
            )
        ]
        director.check_actor_connection()
        tc = director._status
        assert isinstance(tc, ThreadCommand)
        expected = ThreadCommand(ThreadStatus.UPDATE_UI, attribute="do_init", args=[False])
        assert tc.command == expected.command
        assert tc.attribute == expected.attribute
        assert tc.args == expected.args
        assert tc.kwargs == expected.kwargs
