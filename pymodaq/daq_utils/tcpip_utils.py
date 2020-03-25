import numpy as np

##############################
## TCP/IP related functions

def send_string(socket, string):
    """

    Parameters
    ----------
    socket
    string

    Returns
    -------

    """
    cmd_bytes, cmd_length_bytes = message_to_bytes(string)
    check_sended(socket, cmd_length_bytes)
    check_sended(socket, cmd_bytes)

def send_scalar(socket, data):
    """
    Convert it to numpy array then send the data type, the data_byte length and finally the data_bytes
    Parameters
    ----------
    data

    Returns
    -------

    """
    data = np.array([data])
    data_type = data.dtype.descr[0][1]
    data_bytes = data.tobytes()
    send_string(socket, data_type)
    check_sended(socket, len(data_bytes).to_bytes(4, 'big'))
    check_sended(socket, data_bytes)

def get_string(socket):
    string_len = get_int(socket)
    string = check_received_length(socket, string_len).decode()
    return string

def get_int(socket):
    data = int.from_bytes(check_received_length(socket, 4), 'big')
    return data

def get_scalar(socket):
    """

    Parameters
    ----------
    socket

    Returns
    -------

    """
    data_type = get_string(socket)
    data_len = get_int(socket)
    data_bytes = check_received_length(socket, data_len)

    data = np.frombuffer(data_bytes, dtype=data_type)[0]
    return data

def send_list(socket, data_list):
    """

    Parameters
    ----------
    socket
    data_list

    Returns
    -------

    """
    check_sended(socket, len(data_list).to_bytes(4, 'big'))
    for data in data_list:

        if isinstance(data, np.ndarray):
            send_array(socket, data)

        elif isinstance(data, str):
            send_string(socket, data)

        elif isinstance(data, int) or isinstance(data, float):
            send_scalar(socket, data)

def get_list(socket, data_type):
    """
    Receive data from socket as a list
    Parameters
    ----------
    socket: the communication socket
    data_type: either 'string', 'scalar', 'array' depending which function has been used to send the list

    Returns
    -------

    """
    data = []
    list_len = get_int(socket)

    for ind in range(list_len):
        if data_type == 'scalar':
            data.append(get_scalar(socket))
        elif data_type == 'string':
            data.append(get_string(socket))
        elif data_type == 'array':
            data.append(get_array(socket))
    return data

def get_array(socket):
    data_type = get_string(socket)
    data_len = get_int(socket)
    Nrow = get_int(socket)
    Ncol = get_int(socket)
    data_bytes = check_received_length(socket, data_len)

    data = np.frombuffer(data_bytes, dtype=data_type)
    if Ncol != 0:
        data = data.reshape((Nrow, Ncol))
        # data=np.fliplr(data)  #because it gets inverted compared to digital...
    data = np.squeeze(data)  # in case one dimension is 1

    return data



def send_array(socket, data_array):
    """
    get data type as a string
    reshape array as 1D array and get number of rows and cols
    convert Data array as bytes
    send data type
    send data length
    send N rows
    send Ncols
    send data as bytes
    """
    data_type = data_array.dtype.descr[0][1]
    data_shape = data_array.shape
    Nrow = data_shape[0]
    if len(data_shape) > 1:
        Ncol = data_shape[1]
    else:
        Ncol = 1

    data = data_array.reshape(np.prod(data_shape))
    data_bytes = data.tobytes()

    send_string(socket, data_type)

    check_sended(socket, len(data_bytes).to_bytes(4, 'big'))
    check_sended(socket, Nrow.to_bytes(4, 'big'))
    check_sended(socket, Ncol.to_bytes(4, 'big'))
    check_sended(socket, data_bytes)

def message_to_bytes(message):
    """
    Convert a string to a byte array
    Parameters
    ----------
    message (str): message

    Returns
    -------
    Tuple consisting of the message converted as a byte array, and the length of the byte array, itself as a byte array of length 4
    """

    if not isinstance(message, bytes):
        message=message.encode()
    return message,len(message).to_bytes(4, 'big')

def check_sended(socket, data_bytes):
    """
    Make sure all bytes are sent through the socket
    Parameters
    ----------
    socket
    data_bytes

    Returns
    -------

    """
    sended = 0
    while sended < len(data_bytes):
        sended += socket.send(data_bytes[sended:])
    #print(data_bytes)


def check_received_length(sock,length):
    """
    Make sure all bytes (length) that should be received are received through the socket
    Parameters
    ----------
    sock
    length

    Returns
    -------

    """
    l=0
    data_bytes=b''
    while l<length:
        if l<length-4096:
            data_bytes_tmp=sock.recv(4096)
        else:
            data_bytes_tmp=sock.recv(length-l)
        l+=len(data_bytes_tmp)
        data_bytes+=data_bytes_tmp
    #print(data_bytes)
    return data_bytes

##End of TCP/IP functions
##########################
