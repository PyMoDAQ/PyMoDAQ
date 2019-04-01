#!/usr/bin/env python
# coding: utf-8


import socket  
import numpy as np
from pymodaq.daq_viewer.utility_classes import DAQ_TCP_server

def send_command(sock,command="Send Data 0D"):
    """ send one of the message contained in self.message_list toward a socket with identity socket_type
    First send the length of the command with 4bytes
    """
    message,message_length=DAQ_TCP_server.message_to_bytes(command)
    if sock is not None:
        sock.send(message_length)
        sock.send(message_length)
        sock.send(message)

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 6341))
#    
#    send_command(s,"DAQ2D")# just after connect send the client type
#    send_command(s,"Done")
#    send_data(s)
    try:
        send_command(s,"DAQ2D")# just after connect send the client type
        send_command(s,"Send Data 2D")
        data=DAQ_TCP_server.read_data(s,np.float64)
        print(data)
        print(data.shape)
        print(data.dtype)
    except Exception as e:
        print(e)
    finally:
        s.close()
    
    
    
    
    
    
    

