import numpy as np


class Socket:
    def __init__(self, socket=None):
        super().__init__()
        self._socket = socket

    def __eq__(self, other_obj):
        if isinstance(other_obj, Socket):
            other_obj = other_obj.socket
        return self.socket == other_obj

    @property
    def socket(self):
        return self._socket

    def bind(self, *args, **kwargs):
        return self.socket.bind(*args, **kwargs)

    def listen(self, *args, **kwargs):
        return self.socket.listen(*args, **kwargs)

    def getsockname(self, *args, **kwargs):
        return self.socket.getsockname(*args, **kwargs)

    def accept(self):
        sock, addr = self.socket.accept()
        return Socket(sock), addr

    def connect(self, *args, **kwargs):
        return self.socket.connect(*args, **kwargs)

    def send(self, *args, **kwargs):
        return self.socket.send(*args, **kwargs)

    def sendall(self, *args, **kwargs):
        return self.socket.sendall(*args, **kwargs)

    def recv(self, *args, **kwargs):
        return self.socket.recv(*args, **kwargs)

    def close(self):
        return self.socket.close()

    @classmethod
    def message_to_bytes(cls, message):
        """
        Convert a string to a byte array
        Parameters
        ----------
        message (str): message

        Returns
        -------
        Tuple consisting of the message converted as a byte array, and the length of the byte array, itself as a byte array of length 4
        """

        if not isinstance(message, str) and not isinstance(message, bytes):
            message = str(message)
        if not isinstance(message, bytes):
            message = message.encode()
        return message, cls.int_to_bytes(len(message))

    @classmethod
    def int_to_bytes(cls, an_integer):
        if not isinstance(an_integer, int):
            raise TypeError(f'{an_integer} should be an integer, not a {type(an_integer)}')
        return an_integer.to_bytes(4, 'big')

    @classmethod
    def bytes_to_int(cls, bytes_string):
        if not isinstance(bytes_string, bytes):
            raise TypeError(f'{bytes_string} should be an bytes string, not a {type(bytes_string)}')
        assert len(bytes_string) == 4
        return int.from_bytes(bytes_string, 'big')

    def check_sended(self, data_bytes):
        """
        Make sure all bytes are sent through the socket
        Parameters
        ----------
        socket
        data_bytes

        Returns
        -------

        """
        if not isinstance(data_bytes, bytes):
            raise TypeError(f'{data_bytes} should be an bytes string, not a {type(data_bytes)}')
        sended = 0
        while sended < len(data_bytes):
            sended += self.socket.send(data_bytes[sended:])
        #print(data_bytes)


    def check_received_length(self, length):
        """
        Make sure all bytes (length) that should be received are received through the socket
        Parameters
        ----------
        sock
        length

        Returns
        -------

        """
        if not isinstance(length, int):
            raise TypeError(f'{length} should be an integer, not a {type(length)}')

        l = 0
        data_bytes = b''
        while l < length:
            if l < length - 4096:
                data_bytes_tmp = self.socket.recv(4096)
            else:
                data_bytes_tmp = self.socket.recv(length - l)
            l += len(data_bytes_tmp)
            data_bytes += data_bytes_tmp
        # print(data_bytes)
        return data_bytes

    def send_string(self, string):
        """

        Parameters
        ----------
        socket
        string

        Returns
        -------

        """
        cmd_bytes, cmd_length_bytes = self.message_to_bytes(string)
        self.check_sended(cmd_length_bytes)
        self.check_sended(cmd_bytes)

    def get_string(self):
        string_len = self.get_int()
        string = self.check_received_length(string_len).decode()
        return string

    def get_int(self):
        data = self.bytes_to_int(self.check_received_length(4))
        return data

    def send_scalar(self, data):
        """
        Convert it to numpy array then send the data type, the data_byte length and finally the data_bytes
        Parameters
        ----------
        data

        Returns
        -------

        """
        if not (isinstance(data, int) or isinstance(data, float)):
            raise TypeError(f'{data} should be an integer or a float, not a {type(data)}')
        data = np.array([data])
        data_type = data.dtype.descr[0][1]
        data_bytes = data.tobytes()
        self.send_string(data_type)
        self.check_sended(self.int_to_bytes(len(data_bytes)))
        self.check_sended(data_bytes)

    def get_scalar(self):
        """

        Parameters
        ----------
        socket

        Returns
        -------

        """
        data_type = self.get_string()
        data_len = self.get_int()
        data_bytes = self.check_received_length(data_len)

        data = np.frombuffer(data_bytes, dtype=data_type)[0]
        return data

    def get_array(self):
        """get 1D or 2D arrays"""
        data_type = self.get_string()
        data_len = self.get_int()
        shape_len = self.get_int()
        shape = []
        for ind in range(shape_len):
            shape.append(self.get_int())
        data_bytes = self.check_received_length(data_len)
        data = np.frombuffer(data_bytes, dtype=data_type)
        data = data.reshape(tuple(shape))
        return data

    def send_array(self, data_array):
        """send ndarrays

        get data type as a string
        reshape array as 1D array and get the array dimensionality (len of array's shape)
        convert Data array as bytes
        send data type
        send data length
        send data shape length
        send all values of the shape as integers converted to bytes
        send data as bytes
        """
        if not isinstance(data_array, np.ndarray):
            raise TypeError(f'{data_array} should be an numpy array, not a {type(data_array)}')
        data_type = data_array.dtype.descr[0][1]
        data_shape = data_array.shape

        data = data_array.reshape(np.prod(data_shape))
        data_bytes = data.tobytes()

        self.send_string(data_type)
        self.check_sended(self.int_to_bytes(len(data_bytes)))
        self.check_sended(self.int_to_bytes(len(data_shape)))
        for Nxxx in data_shape:
            self.check_sended(self.int_to_bytes(Nxxx))
        self.check_sended(data_bytes)




    def send_list(self, data_list):
        """

        Parameters
        ----------
        socket
        data_list

        Returns
        -------

        """
        if not isinstance(data_list, list):
            raise TypeError(f'{data_list} should be a list, not a {type(data_list)}')
        self.check_sended(self.int_to_bytes(len(data_list)))
        for data in data_list:

            if isinstance(data, np.ndarray):
                self.send_string('array')
                self.send_array(data)

            elif isinstance(data, str):
                self.send_string('string')
                self.send_string(data)

            elif isinstance(data, int) or isinstance(data, float):
                self.send_string('scalar')
                self.send_scalar(data)

            else:
                raise TypeError(f'the element {data} type is cannot be sent by TCP/IP, only numpy arrays'
                                f', strings, or scalars (int or float)')

    def get_list(self):
        """
        Receive data from socket as a list
        Parameters
        ----------
        socket: the communication socket
        Returns
        -------

        """
        data = []
        list_len = self.get_int()

        for ind in range(list_len):
            data_type = self.get_string()
            if data_type == 'scalar':
                data.append(self.get_scalar())
            elif data_type == 'string':
                data.append(self.get_string())
            elif data_type == 'array':
                data.append(self.get_array())
        return data

if __name__ == '__main__':
    from gevent import server, socket
    class SimpleServer(server.StreamServer):
        def __init__(self, *args, handle_fun=lambda x: print('nothing as an handle'), **kwargs):
            super().__init__(*args, **kwargs)
            self.handle_fun = handle_fun

        def handle(self, sock, address):
            self.handle_fun(sock)


    listing = [np.random.rand(7, 2),
               'Hello World',
               1,
               2.654,
               ]

    server = SimpleServer(('127.0.0.1', 0), handle_fun=
    lambda x: Socket(x).send_list(listing))
    server.start()
    client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))

    data = []
    list_len = client.get_int()

    for ind in range(list_len):
        data_type = client.get_string()
        if data_type == 'scalar':
            data.append(client.get_scalar())
        elif data_type == 'string':
            data.append(client.get_string())
        elif data_type == 'array':
            data.append(client.get_array())
    assert data == listing

    client.close()
    server.stop()