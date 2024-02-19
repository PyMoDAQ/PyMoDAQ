
from typing import Optional

import pytest
from pyleco.test import FakeContext
from pyleco.core.message import Message, MessageTypes

from pymodaq.utils.leco.utils import PymodaqMessage, PYMODAQ_MESSAGE_TYPE

from pymodaq.utils.leco.pymodaq_listener import (PymodaqCommunicator, PymodaqPipeHandler,
                                                 PymodaqListener, ListenerSignals)


obj = 123
cid = b"conversation_id;"


@pytest.fixture
def signals() -> ListenerSignals:
    return ListenerSignals()


@pytest.fixture
def pipe_handler(signals) -> PymodaqPipeHandler:
    return PymodaqPipeHandler(name="handler", signals=signals, context=FakeContext())


@pytest.fixture
def communicator(pipe_handler: PymodaqPipeHandler) -> PymodaqCommunicator:
    return pipe_handler.get_communicator()  # type: ignore


@pytest.fixture
def listener() -> PymodaqListener:
    return PymodaqListener(name="listener", context=FakeContext())


def test_communicator_is_pymodaq_communicator(communicator):
    assert isinstance(communicator, PymodaqCommunicator)


class Test_communicator_ask_rpc_pymodaq:
    json_request = PymodaqMessage("remote", "handler", conversation_id=cid,
                                  data={"jsonrpc": "2.0", "id": 1, "method": "test_method"})
    json_response = PymodaqMessage("handler", "remote", conversation_id=cid,
                                   data={"jsonrpc": "2.0", "id": 1, "result": 5})
    pymodaq_request = PymodaqMessage("remote", "handler", pymodaq_data=123, conversation_id=cid,
                                     data={"jsonrpc": "2.0", "id": 1, "method": "test_method"})
    pymodaq_response = PymodaqMessage("handler", "remote", pymodaq_data=123, conversation_id=cid,
                                      data={"jsonrpc": "2.0", "id": 1, "result": None})

    send: Message
    read: Message

    @pytest.fixture
    def communicator_arp(self, communicator: PymodaqCommunicator) -> PymodaqCommunicator:
        def ask_message(message: Message, timeout=None) -> Message:
            if not message.sender:
                message.sender = b"handler"
            message.header = cid + message.header[16:]
            self.send = message
            return self.read

        communicator.ask_message = ask_message  # type: ignore
        return communicator

    def test_send_json_message(self, communicator_arp: PymodaqCommunicator):
        self.read = self.json_response
        communicator_arp.ask_rpc_pymodaq(receiver="remote", method="test_method")
        assert self.send == self.json_request

    def test_send_pymodaq_message(self, communicator_arp: PymodaqCommunicator):
        self.read = self.json_response
        communicator_arp.ask_rpc_pymodaq(receiver="remote", method="test_method", pymodaq_data=obj)
        assert self.send == self.pymodaq_request

    def test_read_json_message(self, communicator_arp: PymodaqCommunicator):
        self.read = self.json_response
        result = communicator_arp.ask_rpc_pymodaq(receiver="remote", method="test_method")
        assert result == 5

    def test_read_pymodaq_message(self, communicator_arp: PymodaqCommunicator):
        self.read = self.pymodaq_response
        result = communicator_arp.ask_rpc_pymodaq(receiver="remote", method="test_method")
        assert result.scalar_deserialization() == obj


class Test_communicator_ask_rpc_flexible:
    json_response = PymodaqMessage("handler", "remote", conversation_id=cid,
                                   data={"jsonrpc": "2.0", "id": 1, "result": 5})

    send: Message
    read: Message

    @pytest.fixture
    def communicator_arp(self, communicator: PymodaqCommunicator) -> PymodaqCommunicator:
        def ask_message(message: Message, timeout=None) -> Message:
            if not message.sender:
                message.sender = b"handler"
            message.header = cid + message.header[16:]
            self.send = message
            return self.read

        communicator.ask_message = ask_message  # type: ignore
        return communicator

    def test_send_json(self, communicator_arp: PymodaqCommunicator):
        obj = {'a': 123.456}  # anything not serializable by pymodaq
        self.read = self.json_response
        communicator_arp.ask_rpc_flexible(receiver="remote", method="some",
                                          pymodaq_data=obj,
                                          pymodaq_data_name="data_field")
        assert self.send == Message(receiver="remote", sender="handler",
                                    message_type=MessageTypes.JSON, conversation_id=cid,
                                    data={"jsonrpc": "2.0", "id": 1, "method": "some",
                                          "params": {"data_field": obj}})

    def test_send_pymodaq(self, communicator_arp: PymodaqCommunicator):
        self.read = self.json_response
        communicator_arp.ask_rpc_flexible(receiver="remote", method="some", pymodaq_data=123,
                                          pymodaq_data_name="data_field")
        # assert
        expected_sent = PymodaqMessage(receiver="remote", sender="handler",
                                       conversation_id=cid, message_type=PYMODAQ_MESSAGE_TYPE,
                                       data={"jsonrpc": "2.0", "id": 1, "method": "some"},
                                       pymodaq_data=123)
        assert self.send == expected_sent


class Test_handler_handle_pymodaq_message:
    msg = PymodaqMessage(receiver="handler", sender="remote", pymodaq_data=123, conversation_id=cid,
                         data={"jsonrpc": "2.0", "id": 1, "method": "checking_values"})

    stored_message: Optional[PymodaqMessage] = None
    previous_stored_data: None
    result: PymodaqMessage

    @pytest.fixture
    def handler_storing_values(self, pipe_handler: PymodaqPipeHandler):
        def checking_values():
            self.stored_message = pipe_handler.current_msg
            self.previous_stored_data = pipe_handler.return_paymodaq_data  # type: ignore
            pipe_handler.return_paymodaq_data = 123

        pipe_handler.register_rpc_method(checking_values)
        # act
        self.result = pipe_handler.handle_pymodaq_message(self.msg)
        return pipe_handler

    def test_stored_message(self, handler_storing_values):
        assert self.stored_message == self.msg

    def test_previous_return_value(self, handler_storing_values):
        assert self.previous_stored_data is None

    def test_response(self, handler_storing_values):
        assert self.result == PymodaqMessage(
            receiver="remote", sender="", data={"jsonrpc": "2.0", "id": 1, "result": None},
            conversation_id=cid, pymodaq_data=123
        )

    def test_temporary_message_cleared_afterwards(self, handler_storing_values: PymodaqPipeHandler):
        assert handler_storing_values.current_msg is None

    def test_temporary_data_cleared_afterwards(self, handler_storing_values: PymodaqPipeHandler):
        assert handler_storing_values.return_paymodaq_data is None
