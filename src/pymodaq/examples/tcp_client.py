"""
Minimal example of a TCP client connecting to a TCP server instrument class plugin (type 0D) and
sending to it 0D data in a row representing a sinus.

To execute all this:

* start a Daq_Viewer from the console, select DAQ0D and TCP_Server, set the IP to localhost, then init
* execute this script

You should see the TCP server printing the sinus in its 0D data viewer

"""


import numpy as np

from pymodaq.utils.tcp_ip.tcp_server_client import TCPClientTemplate
from pymodaq_data.data import DataToExport, DataRaw


class TCPClient(TCPClientTemplate):
    def __init__(self):
        super().__init__(ipaddress="localhost", port=6341, client_type="GRABBER")

    def post_init(self, extra_commands=[]):
        self.socket.check_sended_with_serializer(self.client_type)

    def send_data(self, data: DataToExport):
        # first send 'Done' and then send the length of the list
        if not isinstance(data, DataToExport):
            raise TypeError(f'should send a DataToExport object')
        if self.socket is not None:
            self.socket.check_sended_with_serializer('Done')
            self.socket.check_sended_with_serializer(data)

    def ready_to_read(self):
        message = self._deserializer.string_deserialization()
        self.get_data(message)

    def get_data(self, message: str):
        """

        Parameters
        ----------
        message

        Returns
        -------

        """
        if self.socket is not None:

            if message == 'set_info':
                path = self._deserializer.list_deserialization()
                param_xml = self._deserializer.string_deserialization()
                print(param_xml)

            elif message == 'move_abs' or message == 'move_rel':
                position = self._deserializer.dwa_deserialization()
                print(f'Position is {position}')

            else:
                print(message)

    def data_ready(self, data: DataToExport):
        self.send_data(data)

    def ready_to_write(self):
        pass

    def ready_with_error(self):
        self.connected = False

    def process_error_in_polling(self, e: Exception):
        print(e)



if __name__ == '__main__':
    from threading import Thread
    from time import sleep

    tcpclient = TCPClient()
    t = Thread(target=tcpclient.init_connection)

    t.start()
    sleep(1)
    sinus = np.sin(np.linspace(0, 2 * np.pi, 10))

    for ind in range(10):
        dwa = DataRaw('mydata', data=[np.array([sinus[ind]])], plot=True)
        tcpclient.data_ready(dwa.as_dte())

    tcpclient.close()



