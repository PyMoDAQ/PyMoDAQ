
from typing import Any, Optional, Union

from pyleco.core.message import Message, MessageTypes
from pymodaq.utils.tcp_ip.serializer import Serializer, DeSerializer, SERIALIZABLE

PYMODAQ_MESSAGE_TYPE = 131


def get_pymodaq_data(message: Message) -> Optional[DeSerializer]:
    """Get the pymodaq DeSerializer object of a message."""
    if message.header_elements.message_type == PYMODAQ_MESSAGE_TYPE and len(message.payload) > 1:
        return DeSerializer(message.payload[1])
    else:
        return None


class PymodaqMessage(Message):
    """A LECO message with a pymoaq object as additional `payload` frame.

    The first payload frame contains the JSON message.
    If there is a `pymodaq_data` argument, this object will be serialized in the second payload
    frame. In this case, the message_type is changed to pymodaq message type.

    The :attr:`pymodaq_data` attribute contains a pymodaq DeSerializer object of the content.
    """

    def __init__(self,
                 receiver: Union[bytes, str],
                 sender: Union[bytes, str] = b"",
                 data: Optional[Union[bytes, str, Any]] = None,
                 pymodaq_data: Optional[SERIALIZABLE] = None,
                 header: Optional[bytes] = None,
                 conversation_id: Optional[bytes] = None,
                 message_id: Optional[bytes] = None,
                 message_type: Union[MessageTypes, int] = MessageTypes.JSON,
                 ) -> None:
        if pymodaq_data:
            message_type = PYMODAQ_MESSAGE_TYPE
        super().__init__(receiver, sender, data, header, conversation_id, message_id, message_type)
        if pymodaq_data:
            self.payload.append(Serializer(pymodaq_data).to_bytes())

    @property
    def pymodaq_data(self) -> Optional[DeSerializer]:
         return get_pymodaq_data(message=self)
