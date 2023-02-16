.. _tcpip:

TCP/IP communication
====================

This section is for people who want an answer to: *I have a detector or an actuator controlled on a distant computer and
cannot have it on the main computer, do you have a solution?*

The answer is of course : *YES*

For this, you have two options:

* install PyMoDAQ to control your hardware on the distant computer
* Use a software on the distant computer that can use TCP/IP communication following the rules given below

With PyMoDAQ
++++++++++++

From version 1.6.0, each actuator (DAQ_Move) or detector (DAQ_Viewer) module can be connected to their counterpart on a
distant computer. For both modules, a TCPServer plugin is available and can be initialized. It will serve as a bridge
between the main computer, running for instance a DAQ_Scan module, and the distant one running a usual DAQ_Move or DAQ_Viewer
module, see :numref:`tcpip_scheme`. Every parameter of the distant module will be exported on its server counterpart. Any modification
of these parameters, either on the server or on the local module, will be updated on either the local module or the server module.


   .. _tcpip_scheme:

.. figure:: /image/tcpip.png
   :alt: tcpip

   Typical configuration with modules on distant computers communicating over a TCP/IP connection

On another software
+++++++++++++++++++

The TCP_server plugin can also be used as a bridge between PyMoDAQ and another custom software (installed locally or
on a distant computer) able to initialize a TCP client and understand PyMoDAQ's TCP/IP communications. For instance, at
CEMES, we've build such a bridge between Digital Micrograph running (eventually) on a distant computer and controlling
a specific Gatan camera on an electron microscope. The communication framework used by PyMoDAQ is as follow:

Making sure messages are complete:
----------------------------------

Message send on a tcp/ip connection can sometimes be send as chunks, it is therefore important to know what will be the
length of the message to be sent or to be received. PyMoDAQ use the following methods to make sure the message is
entirely send or entirely received:

.. code-block:: python

    def check_received_length(sock,length):
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

    def check_sended(socket, data_bytes):
        sended = 0
        while sended < len(data_bytes):
            sended += socket.send(data_bytes[sended:])

Sending and receiving commands (or message):
--------------------------------------------

Commands are strings that should be either:

* Client receiving messages:
    * For all modules: ``Info``, ``Infos``, ``Info_xml``, ``set_info``
    * For a detector:  ``Send Data 0D``, ``Send Data 1D``, ``Send Data 2D``
    * For an actuator: ``move_abs``, ``move_home``, ``move_rel``, ``check_position``, ``stop_motion``
* Client sending messages:
    * For all modules: ``Quit``, ``Done``, ``Info``, ``Infos``, ``Info_xml``
    * For a detector:  ``x_axis``, ``y_axis``
    * For an actuator: ``position_is``, ``move_done``


The principles of communication within PyMoDAQ are summarized on figure :numref:`tcpip_fig` and as follow:

To be send, the string is converted to bytes. The length of this converted string is then computed and also converted to bytes. The
converted length is first send through the socket connection and then the converted command is also sent as follow:

.. code-block:: python

    def message_to_bytes(message):
        if not isinstance(message, bytes):
            message=message.encode()
        return message,len(message).to_bytes(4, 'big') #4 bytes to encode the length as an integer

    string = 'Send Data 2D'

    cmd_bytes, cmd_length_bytes = message_to_bytes(string)
    check_sended(socket, cmd_length_bytes) #first send the length of the message
    check_sended(socket, cmd_bytes) #then send the converted message

For the message to be properly received, the client listen on the socket. The first bytes to arrive represent the length
of the message (number of bytes)

.. code-block:: python

    def get_string(socket):
        string_len = get_int(socket) #receive first the length of the message
        string = check_received_length(socket, string_len).decode() #then read length bytes, and decode it to string
        return string

    def get_int(socket):
        data = int.from_bytes(check_received_length(socket, 4), 'big') #read 4 bytes to compose the length of the message
        return data

    message = get_string(self.socket)

For the detail of the python utility functions used to convert, send and receive data see the ``pymodaq.utils.tcpip_utils``
module and its API (:ref:`tcpip_API`).

   .. _tcpip_fig:

.. figure:: /image/tcp_ip.png
   :alt: tcp_ip_communication

   Diagram principle of PyMoDAQ message communication through a TCP/IP socket.



Sending and receiving Datas:
----------------------------

Sending or receiving datas is very similar to messages except that datas have a type (integer, float...) and have also a
dimensionality: 0D, 1D, ... Moreover, the datas exported from plugins and viewers are almost always numpy arrays within
a list. One should therefore take all this into consideration. The principles of data communication are summarized on
diagram :numref:`tcpip_fig_data`

   .. _tcpip_fig_data:

.. figure:: /image/tcp_ip_data.png
   :alt: tcp_ip_communication

   Diagram principle of PyMoDAQ data communication through a TCP/IP socket for a list of datas.

Custom client: how to?
----------------------

#. The TCP/Client should first try to connect to the server (using TCP server PyMoDAQ plugin), once the connection is
   accepted, it should send an identification, the ``client type`` (*GRABBER* or *ACTUATOR* command)
#. (optional) Then it can send some information about its configuration as an xml string following the
   ``pymodaq.utils.custom_parameter_tree.parameter_to_xml_string`` method.
#. Then the client enters a loop waiting for input from the server and is ready to read commands on the socket
#. Receiving commands
    * For a detector:  ``Send Data 0D``, ``Send Data 1D``, ``Send Data 2D``
    * For an actuator: ``move_abs``, ``move_home``, ``move_rel``, ``check_position``, ``stop_motion``
#. Processing internally the command
#. Giving a reply
    * For a detector:
        * Send the command ``Done``
        * Send the datas as a list of arrays
    * For an actuator:
        * Send a reply depending on the one it received:
            * ``move_done`` for ``move_abs``, ``move_home``, ``move_rel`` commands
            * ``position_is`` for ``check_position`` command
        * Send the position as a scalar (see below)

.. code-block:: python

    def send_scalar(socket, data):
        data = np.array([data])
        data_type = data.dtype.descr[0][1]
        data_bytes = data.tobytes()
        send_string(socket, data_type)
        check_sended(socket, len(data_bytes).to_bytes(4, 'big'))
        check_sended(socket, data_bytes)


Pretty easy, isn't it?

Well, if it isn't you can have a look in the example folder where a Labview based TCP client has been
programed. It emulates all the rules stated above, and if you are a Labview user, you're lucky ;-) but should really
think on moving on to python with PyMoDAQ...

