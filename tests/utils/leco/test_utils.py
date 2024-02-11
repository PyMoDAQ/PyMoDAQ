
import pytest

from pyleco.core.message import MessageTypes

from pymodaq.utils.leco.utils import PymodaqMessage, Serializer, PYMODAQ_MESSAGE_TYPE


receiver = b"receiver"
sender = b"sender"
obj = 123


class Test_PymodaqMessage_creator_without_pymodaq_payload:
    @pytest.fixture
    def pymodaq_message(self) -> PymodaqMessage:
        pmd_message = PymodaqMessage(receiver, sender, data="[5, 6.7]")
        return pmd_message

    def test_type_json(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.header_elements.message_type == MessageTypes.JSON

    def test_receiver(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.receiver == receiver

    def test_data(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.data == [5, 6.7]

    def test_pymodaq_data(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.pymodaq_data is None


class Test_PymodaqMessage_creator_with_pymodaq_payload:
    @pytest.fixture
    def pymodaq_message(self) -> PymodaqMessage:
        pmd_message = PymodaqMessage(receiver, sender, data="[5, 6.7]",
                                     pymodaq_data=obj)
        return pmd_message

    def test_type_json(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.header_elements.message_type == PYMODAQ_MESSAGE_TYPE

    def test_receiver(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.receiver == receiver

    def test_data(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.data == [5, 6.7]

    def test_payload(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.payload[1] == Serializer(obj).to_bytes()

    def test_pymodaq_data(self, pymodaq_message: PymodaqMessage):
        assert pymodaq_message.pymodaq_data.scalar_deserialization() == obj  # type: ignore
