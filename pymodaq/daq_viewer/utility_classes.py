from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize

import sys
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from easydict import EasyDict as edict
import socket, select
import numpy as np
from pymodaq.daq_utils.daq_utils import gauss1D, gauss2D
from collections import OrderedDict
from pymodaq.daq_utils.daq_utils import ThreadCommand, ScanParameters

comon_parameters=[{'title': 'Controller Status:', 'name': 'controller_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},]


class DAQ_Viewer_base(QObject):
    """
        ===================== ===================================
        **Attributes**          **Type**
        *hardware_averaging*    boolean
        *data_grabed_signal*    instance of pyqtSignal
        *params*                list
        *settings*              instance of pyqtgraph Parameter
        *parent*                ???
        *status*                dictionnary
        ===================== ===================================

        See Also
        --------
        send_param_status
    """
    hardware_averaging=False
    data_grabed_signal=pyqtSignal(list)
    data_grabed_signal_temp=pyqtSignal(list)

    params = []
    def __init__(self,parent=None,params_state=None):
        super(DAQ_Viewer_base, self).__init__()
        self.parent_parameters_path = [] #this is to be added in the send_param_status to take into account when the current class instance parameter list is a child of some other class
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())


        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.parent = parent
        self.status = edict(info="",controller=None,initialized=False)
        self.scan_parameters = None

    def emit_status(self,status):
        """
            Emit the status signal from the given status.

            =============== ============ =====================================
            **Parameters**    **Type**     **Description**
            *status*                       the status information to transmit
            =============== ============ =====================================
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
            QtWidgets.QApplication.processEvents()
        else:
            print(*status)

    @pyqtSlot(ScanParameters)
    def update_scanner(self, scan_parameters):
        self.scan_parameters = scan_parameters

    def update_com(self):
        """
        If some communications settings have to be reinit
        Returns
        -------

        """
        pass

    @pyqtSlot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update the settings tree from settings_parameter_dict.
            Finally do a commit to activate changes.
            
            ========================== ============= =====================================================
            **Parameters**              **Type**      **Description**
            *settings_parameter_dict*   dictionnnary  a dictionnary listing path and associated parameter
            ========================== ============= =====================================================

            See Also
            --------
            send_param_status, commit_settings
        """
            # settings_parameter_dict=edict(path=path,param=param)
        try:
            path = settings_parameter_dict['path']
            param = settings_parameter_dict['param']
            change = settings_parameter_dict['change']
            try:
                self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
            except: pass
            if change == 'value':
                self.settings.child(*path[1:]).setValue(param.value()) #blocks signal back to main UI
            elif change == 'childAdded':
                child = Parameter.create(name = 'tmp')
                child.restoreState(param)
                self.settings.child(*path[1:]).addChild(child) #blocks signal back to main UI


            elif change == 'parent':
                children = custom_tree.get_param_from_name(self.settings, param.name())

                if children is not None:
                    path = custom_tree.get_param_path(children)
                    self.settings.child(*path[1:-1]).removeChild(children)

            self.settings.sigTreeStateChanged.connect(self.send_param_status)

            self.commit_settings(param)
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def commit_settings(self,param):
        """
            Not implemented.
        """
        pass

    def stop(self):
        pass


    def send_param_status(self,param,changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, send the 'update_settings' ThreadCommand with concerned path,data and change as attributes.

            =============== ============================================ ============================
            **Parameters**    **Type**                                    **Description**
            *param*           instance of pyqtgraph parameter             The parameter to check
            *changes*         (parameter,change,information) tuple list   The changes list to course
            =============== ============================================ ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                #first create a "copy" of the actual parameter and send this "copy", to be restored in the main UI
                self.emit_status(ThreadCommand('update_settings',[self.parent_parameters_path+path, [data[0].saveState(), data[1]], change])) #send parameters values/limits back to the GUI. Send kind of a copy back the GUI otherwise the child reference will be the same in both th eUI and the plugin so one of them will be removed

            elif change == 'value' or change == 'limits' or change == 'options':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path+path, data, change])) #send parameters values/limits back to the GUI
            elif change == 'parent':
                pass

            pass

    def emit_x_axis(self):
        """
            Convenience function
            Emit the thread command "x_axis" with x_axis as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand("x_axis",[self.x_axis]))

    def emit_y_axis(self):
        """
            Emit the thread command "y_axis" with y_axis as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand("y_axis",[self.y_axis]))
 
class DAQ_TCP_server(DAQ_Viewer_base):
    """
        ==================== ===============================
        **Attributes**         **Type**
        *message_list*         string list
        *socket_types*         string list
        *params*               dictionnary list
        *ind_data*             int
        *data_mock*            double precision float array
        *connected_clients*    list
        *listening*            boolean
        *processing*           ???
        ==================== ===============================
    """
    message_list=["Quit","Send Data 0D","Send Data 1D","Send Data 2D","Status","Done","Server Closed","Info"]
    socket_types=["DAQ0D","DAQ1D","DAQ2D","GRABBER"]
    params= comon_parameters+[{'title': 'Port:', 'name': 'port_id', 'type': 'int', 'value': 6341 , 'default':6341},
             {'title': 'IP:', 'name': 'socket_ip', 'type': 'str', 'value': 'localhost' , 'default':'10.47.1.33'},
             {'title': 'Timeout (s):', 'name': 'listen_timeout', 'type': 'int','value': 10, 'default': 10},
             {'title': 'Data type:', 'name': 'data_type', 'type': 'list', 'value':np.float32, 'values': {'int8': np.uint8, 'int16': np.uint16, 'int32': np.uint32,'float32': np.float32, 'float64': np.float64, }, 'default':''},
             {'title': 'Exposure (s):', 'name': 'exposure', 'type': 'float','value': 0, 'default': 0, 'readonly': True},
             {'title': 'Nx:', 'name': 'Nx', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
             {'title': 'Ny:', 'name': 'Ny', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
             {'title': 'binx:', 'name': 'binx', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
             {'title': 'biny:', 'name': 'biny', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
             {'title': 'Connected clients:', 'name': 'conn_clients', 'type': 'table', 'value': dict() , 'header':['Type','adress']},
             ]

    def __init__(self,parent=None,params_state=None):
        """
            Parameters
            ----------
            Ip: str
                either None (then one use socket.gethostname()) or 'localhost' or '127.0.0.1' or '' for all available ressource
            port: int
                the port on which we want to communicate
        """

        super(DAQ_TCP_server,self).__init__(parent,params_state)
        self.ind_data=0
        self.data_mock=None
        self.connected_clients=[]
        self.listening=True
        self.processing=False
        #self.init_server()
            
    @pyqtSlot(list)
    def queue_command(self,command):
        """
            Treat the given command.
            In case of :
            * 'Ini_Server' command name : update status attribute with init_server function
            * 'process_cmds' command name : process  the 'Send Data 2D' command.

            =============== ============== ================================================
            **Parameters**    **Type**       **Description**
            *command*         string list    a string list representing the command socket
            =============== ============== ================================================

            See Also
            --------
            init_server, process_cmds
        """
        if command[0]=="Ini_Server":
            status=self.init_server()
        elif command[0]=="process_cmds":
            self.process_cmds("Send Data 2D")
                                                 
    def close_server(self):
        """
            close the current opened server.
            Update the settings tree consequently.

            See Also
            --------
            set_connected_clients_table, daq_utils.ThreadCommand
        """
        for sock_dict in self.connected_clients:
            try:
                sock_dict['socket'].close()
            except: pass
        self.connected_clients=[]
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

    def init_server(self):
        self.emit_status(ThreadCommand("Update_Status",["Started new server for {:s}:{:d}".format(self.settings.child(('socket_ip')).value(),self.settings.child(('port_id')).value()),'log']))
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to a public host, and a well-known port
        try:
            self.serversocket.bind((self.settings.child(('socket_ip')).value(),self.settings.child(('port_id')).value()))
        except socket.error as msg:
            self.emit_status(ThreadCommand("Update_Status",['Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror,'log']))
            raise Exception('Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror)
        
        self.serversocket.listen(5)
        self.connected_clients.append(dict(socket=self.serversocket,type='server'))
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

        self.timer=self.startTimer(100) #Timer event fired every 100ms
        #self.listen_client()

        

    def timerEvent(self, event):
        """
            Called by set timers. 
            If the process is free, start the listen_client function.

            =============== ==================== ==============================================
            **Parameters**   **Type**              **Description**

            *event*          QTimerEvent object    Containing id from timer issuing this event
            =============== ==================== ==============================================

            See Also
            --------
            listen_client
        """
        if not self.processing:
            self.listen_client()

    def set_connected_clients_table(self):
        """

        """
        con_clients=OrderedDict()
        for socket_dict in self.connected_clients:
            try:
                address=str(socket_dict['socket'].getsockname())
            except:
                address=""
            con_clients[socket_dict['type']]=address
        return con_clients

    @pyqtSlot(list)
    def print_status(self,status):
        """
            Print the given status.

            =============== ============= ================================================
            **Parameters**    **Type**       **Description**
            *status*          string list    a string list representing the status socket
            =============== ============= ================================================
        """
        print(status)


    def listen_client(self):
        """
            Server function.
            Used to listen incoming message from a client.
            Start a connection and :
            * if current socket corresponding to the serversocket attribute :

                * Read received command
                * Send the 'Update_Status' thread command if needed (log is not valid)

            * Else, in case of :

                * data received from client : process it reading commands from sock. Process the command or quit if asked.
                * client disconnected : remove from socket list
                

            See Also
            --------
            find_socket_type_within_connected_clients, set_connected_clients_table, daq_utils.ThreadCommand, read_commands, process_cmds, utility_classes.DAQ_Viewer_base.emit_status
        """
        try:
            self.processing=True
            #QtWidgets.QApplication.processEvents() #to let external commands in
            read_sockets,write_sockets,error_sockets = select.select([client['socket'] for client in self.connected_clients],[],[client['socket'] for client in self.connected_clients],self.settings.child(('listen_timeout')).value())
            for sock in error_sockets:
                sock_type=self.find_socket_type_within_connected_clients(sock)
                if sock_type is not None:
                    self.connected_clients.remove(dict(socket=sock,type=sock_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    try:
                        sock.close()
                    except: pass
                    self.emit_status(ThreadCommand("Update_Status",['Client '+sock_type+' disconnected','log']))

            for sock in read_sockets:
                QThread.msleep(100)
                #New connection
                if sock == self.serversocket:
                    (client_socket, address) = self.serversocket.accept()
                    #client_socket.setblocking(False)
                    DAQ_type=self.read_commands(client_socket)
                    if DAQ_type not in self.socket_types:
                        self.emit_status(ThreadCommand("Update_Status",[DAQ_type+' is not a valid type','log']))
                        break

                    self.connected_clients.append(dict(socket=client_socket,type=DAQ_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    self.emit_status(ThreadCommand("Update_Status",[DAQ_type+' connected with ' + address[0] + ':' + str(address[1]),'log']))
                    QtWidgets.QApplication.processEvents()
                #Some incoming message from a client
                else:
                    # Data received from client, process it
                    try:
                        message=self.read_commands(sock)
                        if message == 'Done' or message == 'Info':
                            self.process_cmds(message)
                        elif message == 'Quit':
                            raise Exception("socket disconnect by user")
                        else:
                            self.process_cmds(message,command_sock=sock)
                        
                    # client disconnected, so remove from socket list
                    except Exception as e:
                        sock_type=self.find_socket_type_within_connected_clients(sock)
                        if sock_type is not None:
                            self.connected_clients.remove(dict(socket=sock,type=sock_type))
                            self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                            #sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                            self.emit_status(ThreadCommand("Update_Status",['Client '+sock_type+' disconnected','log']))

            self.processing=False

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def read_commands(self,sock):
        """
            Read the commands from the given socket.
            
            =============== ============
            **Parameters**    **Type**
            *sock*  
            =============== ============
            
            Returns
            -------
            message_bytes
                The readed and decoded message

            See Also
            --------
            check_received_length
        """

        length_bytes = self.check_received_length(sock,4)
        length=np.fromstring(length_bytes,dtype=np.int32)[0].byteswap()
        self.check_received_length(sock,4)
        message_bytes=self.check_received_length(sock,length)
        message=message_bytes.decode() #checkout the presence of 4 (or not) comes from labview shitty stuff
        return message

    def send_command(self,sock,command="Send Data 0D"):
        """ 
            Send one of the message contained in self.message_list toward a socket with identity socket_type.
            First send the length of the command with 4bytes.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *sock*             ???        The current socket
            *command*         string      The command as a string
            =============== =========== ==========================

            See Also
            --------
            utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, message_to_bytes
        """
        if command not in self.message_list:
            self.emit_status(ThreadCommand("Update_Status",['Command: '+str(command) +' not in the specified list','log']))
            return

        message,message_length=self.message_to_bytes(command)
        if sock is not None:
            sock.send(message_length)
            sock.send(message_length)
            sock.send(message)

    def find_socket_within_connected_clients(self,client_type):
        """
            Find a socket from a conneceted client with socket type corresponding.

            =============== =========== ================================
            **Parameters**    **Type**    **Description**
            *client_type*      string     The corresponding client type
            =============== =========== ================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res=None
        for socket_dict in self.connected_clients:
            if socket_dict['type']==client_type:
                res=socket_dict['socket']
        return res

    def find_socket_type_within_connected_clients(self,sock):
        """
            Find a socket type from a connected client with socket content corresponding.

            =============== =========== ===================================
            **Parameters**    **Type**   **Description**
            *sock*             ???       The socket content corresponding.
            =============== =========== ===================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res=None
        for socket_dict in self.connected_clients:
            if socket_dict['socket']==sock:
                res=socket_dict['type']
        return res

    def process_cmds(self,command,command_sock=None):
        """
            Process the given command.

            Depending on the command name :
            * Done : 

                * Find a socket from the 'GRABBER' connected client.
                * Send data to a viewer or a client (depending on command_sock).

            * Info : Find a socket from the 'GRABBER' connected client and read infos. 

            * Send Data 0D : 

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 1D : 

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 2D : 
            
                * Find a socket from the 'GRABBER' connected client.
                * set a 2D Mock data.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *command*         string      the command as a string
            *command_sock*    ???
            =============== =========== ==========================   

            See Also
            --------
            find_socket_within_connected_clients, read_data, send_data, utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, send_command, set_1D_Mock_data, set_2D_Mock_data, process_cmds           
        """
        if command not in self.message_list:
            return

        if command=='Done': #means the given socket finished grabbing data and is ready to send them
            try:
                sock=self.find_socket_within_connected_clients('GRABBER')
                if sock is not None: #if client 'GRABBER' is connected then send it the command
                    data=self.read_data(sock,self.settings.child(('data_type')).value())
                else:
                    data=self.data_mock

                if command_sock is None:
                    self.data_grabed_signal.emit([OrderedDict(data=[data],name='TCP GRABBER', type='Data2D')]) #to be directly send to a viewer
                    #print(data)
                else:
                    self.send_data(command_sock,data) #to be send to a client

            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

        elif command=="Info":
            try:
                sock=self.find_socket_within_connected_clients('GRABBER')
                if sock is not None: #if client 'GRABBER' is connected then send it the command
                    self.read_info(sock)


            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))


        elif command=="Send Data 0D" or command=="Send Data 1D" or command=="Send Data 2D":
            sock=self.find_socket_within_connected_clients('GRABBER')
            if sock is not None: #if client 'GRABBER' is connected then send it the command
                self.send_command(sock,command)

            else:#else simulate mock data
                if command=="Send Data 0D":
                    self.set_1D_Mock_data()
                    self.data_mock=np.array([self.data_mock[0]])
                elif command=="Send Data 1D":
                    self.set_1D_Mock_data()
                    data=self.data_mock
                elif command=="Send Data 2D":
                    self.set_2D_Mock_data()
                    data=self.data_mock
                self.process_cmds('Done')


        else:
            pass

    def read_info(self,sock,dtype=np.float64):
        """
            Read the 64bits float informations contained in the given socket in three steps :
                * get the info type.
                * get data length.
                * get data.

            
            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *sock*             ???                 the socket to be readed
            *dtype*           numpy float 64bits   ???
            =============== ===================== =========================

            Returns
            -------
            big indian 64bits float 
                the readed data.

            See Also
            --------
            check_received_length, utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand
        """
        try:

            ##first get the info type
            length_bytes=self.check_received_length(sock,4)
            length=np.fromstring(length_bytes,dtype='>i4')[0] #big endian 4 bytes==uint32 swaped
            self.check_received_length(sock,4)
            message=self.check_received_length(sock,length).decode()

            #get data length
            length_bytes = self.check_received_length(sock,4)
            length=np.fromstring(length_bytes,dtype='>i4')[0]



            ##then get data
            data_bytes=self.check_received_length(sock,length)

            data=np.fromstring(data_bytes,dtype=dtype)
            data=data.newbyteorder()[0] #convert it to big endian
            try:
                self.settings.child((message)).setValue(data)
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
  
        except Exception as e:
            data=0

        return data


    def read_data(self,sock,dtype=np.uint32):
        """
            Read the unsigned 32bits int data contained in the given socket in five steps :
                * get back the message
                * get the data length
                * get the number of row
                * get the number of column
                * get data

            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *sock*              ???                the socket to be readed
            *dtype*           numpy unint 32bits   ???
            =============== ===================== =========================

            See Also
            --------
            check_received_length
        """
        try:
            ##first get back the message
            length_bytes=self.check_received_length(sock,4)
            length=np.fromstring(length_bytes,dtype='>i4')[0] #big endian 4 bytes==uint32 swaped
            self.check_received_length(sock,4)
            message_bytes=self.check_received_length(sock,length)

            #get data length
            length_bytes = self.check_received_length(sock,4)
            length=np.fromstring(length_bytes,dtype='>i4')[0]

            ##then get Nrow
            Nrow = self.check_received_length(sock,4)
            Nrow=np.fromstring(Nrow,dtype='>i4')[0]

            ##then get Ncol
            Ncol = self.check_received_length(sock,4)
            Ncol=np.fromstring(Ncol,dtype='>i4')[0]

            ##then get data
            data_bytes=self.check_received_length(sock,length)

            data=np.fromstring(data_bytes,dtype=dtype)
            data=data.newbyteorder() #convert it to big endian
            #data=np.array([[1,2,3],[1,2,3]])

            if Ncol!=0:
                data=data.reshape((Nrow,Ncol))
                data=np.fliplr(data)  #because it gets inverted compared to digital...     
        except Exception as e:
            data=np.zeros((Nrow,Ncol))

        return data

    def check_received_length(self,sock,length):
        """
            Check the received length compared to the effective received data bytes.

            =============== =========== ====================
            **Parameters**    **Type**   **Description**
            *sock*            ???        the readed socket
            *length*          int        the expected length
            =============== =========== ====================
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

        return data_bytes


    def send_data(self,sock,data):
        """
            To match digital and labview, send again a command.

            =============== ============================== ====================
            **Parameters**   **Type**                       **Description**
            *sock*                                          the socket receipt
            *data*           double precision float array   the data to be sent
            =============== ============================== ====================

            See Also
            --------
            send_command, check_send_data
        """
        self.send_command(sock,'Done')

        if len(data.shape)==0:
            Nrow=1
            Ncol=0
        elif len(data.shape)==1:
            Nrow=data.shape[0]
            Ncol=0
        elif len(data.shape)==2:
            Nrow=data.shape[0]
            Ncol=data.shape[1]
        data_bytes=data.tobytes()
    
        sock.send(np.array([len(data_bytes)],dtype='>i4').tobytes())#first send length of data after reshaping as 1D bytes array
        sock.send(np.array([Nrow],dtype='>i4').tobytes()) #then send dimension of lines
        sock.send(np.array([Ncol],dtype='>i4').tobytes()) #then send dimensions of columns
        
        self.check_send_data(sock,data_bytes) #then send data

    def check_send_data(self,sock,data):
        """
            Check the sent data.
        """
        L=len(data)
        l=sock.send(data)
        while l<L:
            l+=sock.send(data[l:])


    @staticmethod
    def message_to_bytes(message):
        """
            Convert message to bytes

        =============== =========== ============================
        **Parameters**    **Type**   **Description**
  
        *message*          string     message to be sent around
        =============== =========== ============================
        
        *message* value in ["Quit","Send Data 0D","Send Data 1D","Send Data 2D","Status","Done","Server Closed"]

        Returns
        -------
        message_bytes : bytes array
            encoded version of message
        bytes array:
            int32 length of message bytes as a 4 bytes array
        """

        message_bytes=message.encode()
        return message_bytes, np.array([len(message_bytes)],dtype=np.int32).byteswap().tobytes()

    def set_1D_Mock_data(self):
        self.data_mock
        x=np.linspace(0,99,100)
        data_tmp=10*gauss1D(x,50,10,1)+1*np.random.rand((100))
        self.ind_data+=1
        self.data_mock=np.roll(data_tmp,self.ind_data)
        self.data_mock=self.data_mock.astype(self.settings.child(('data_type')).value())

    def set_2D_Mock_data(self):
        self.x_axis=np.linspace(0,50,50,endpoint=False)
        self.y_axis=np.linspace(0,30,30,endpoint=False)
        self.data_mock=10*gauss2D(self.x_axis,20,10,
                                  self.y_axis,15,7,1)+2*np.random.rand(len(self.y_axis),len(self.x_axis))
        self.data_mock=self.data_mock.astype(self.settings.child(('data_type')).value())

        




if __name__ == '__main__':
    prog = DAQ_TCP_server()