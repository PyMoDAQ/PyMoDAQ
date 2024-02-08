
from typing import Any, Optional, Union

from pyleco.core.message import Message, MessageTypes
from pymodaq.utils.tcp_ip.serializer import Serializer

PYMODAQ_MESSAGE_TYPE = 131


def create_pymodaq_message(receiver: Union[bytes, str],
                           data: Union[bytes, str, Any, None],
                           conversation_id: Optional[bytes] = None,
                           pymodaq_data: Optional[Any] = None
                           ) -> Message:
    """Create a message with optionally a pymodaq object as additional payload."""
    message = Message(receiver=receiver, data=data, conversation_id=conversation_id,
                      message_type=PYMODAQ_MESSAGE_TYPE if pymodaq_data else MessageTypes.JSON,
                      )
    if pymodaq_data:
        message.payload.append(Serializer(pymodaq_data).to_bytes())
    return message
