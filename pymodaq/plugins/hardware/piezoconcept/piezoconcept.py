import pyvisa

class Position(object):
    units=['n','u']
    axes=['X','Y']
    def __init__(self,axis='X',pos=100., unit='u'):
        if axis in self.axes:
            self.axis=axis
        else:
            raise Exception('{:s} is not a valid axis'.format(axis))
        self.pos=pos
        if unit in self.units:
            self.unit=unit
        else:
            raise Exception('{:s} is not a valid unit'.format(unit))
        
    def __str__(self):
        return 'Axis {:s} at position {:f}{:s}'.format(self.axis, self.pos, self.unit)    
    
    def __repr__(self):
        return self.__str__()
    
class Time(object):
    units=['u','m','s'] #valid units
    def __init__(self,time=100., unit='u'):
        self.time=time
        if unit in self.units:
            self.unit=unit
        else:
            raise Exception('{:s} is not a valid unit'.format(unit))
            
    def __str__(self):
        return 'Time: {:f}{:s}'.format(self.time, self.unit)    
    
    def __repr__(self):
        return self.__str__()  
    
class PiezoConcept(object):
    
    def __init__(self):
        super(PiezoConcept,self).__init__()
        self._piezo=None
        self._VISA_rm=pyvisa.ResourceManager()
        self.com_ports=self.get_ressources()
        self.timeout=2000 #by default

    def get_ressources(self):
        infos=self._VISA_rm.list_resources_info()
        com_ports=[infos[key].alias for key in infos.keys()]
        return com_ports
    
    def init_communication(self,com_port):
        com_port='COM9'
        if com_port in self.com_ports:
            self._piezo=self._VISA_rm.open_resource(com_port)
            #set attributes
            self._piezo.baud_rate=115200
            self._piezo.data_bits=8
            self._piezo.stop_bits=pyvisa.constants.StopBits['one']
            self._piezo.parity=pyvisa.constants.Parity['none']
            self._piezo.flow_control=0
            self._piezo.read_termination=self._piezo.LF
            self._piezo.write_termination=self._piezo.LF
            self._piezo.timeout=self.timeout
        else:
            raise IOError('{:s} is not a valid port'.format(com_port))
            
    def close_communication(self):
        self._piezo.close()
        self._VISA_rm.close() 
        
    def get_controller_infos(self):
        self._piezo.write('INFOS')
        return self.get_read()
            
    def write_command(self,command):
        self._piezo.write(command)
        if self._piezo.read(encoding='mbcs')!='Ok':
            raise IOError('wrong return from controller')
    
    def get_read(self):
        self._piezo.timeout=100
        info=''
        try:
            while True:
                info+=self._piezo.read(encoding='mbcs')+'\n'
        except pyvisa.errors.VisaIOError as e:
            pass
        self._piezo.timeout=self.timeout
        return info
    
    def move_axis(self,move_type='ABS',pos=Position(axis='X',pos=100,unit='u')):
        if move_type=='ABS':
            self.write_command('MOVE{:s} {:f}{:s}'.format(pos.axis,pos.pos,pos.unit))
        elif move_type=='REL':
            self.write_command('MOVR{:s} {:f}{:s}'.format(pos.axis,pos.pos,pos.unit))
        else:
            raise Exception('{:s} is not a valid displacement type'.format(move_type))


    def get_position(self,axis='X'):
        """ return the given axis position
        Parameters
        ----------
        axis: str, default 'X'
            either 'X' or 'Y'
        Returns
        -------
        pos
            an instance of the Position class containing the attributes:
                axis (either ('X' or 'Y'), pos and unit (either 'u' or 'n')
        """    
        pos_str=self._piezo.query('GET_{:s}'.format(axis))
        pos=Position(axis,float(pos_str[0:-3]),pos_str[-2])
        return pos

    def set_time_interval(self,time=Time(50.,'m')):
        if type(time)==Time:
            self.write_command('STIME {:d}{:s}'.format(time.time,time.unit))
        else:
            raise Exception('Wrong time argument')
            
    def get_time_interval(self):
        time_str=self._piezo.query('GTIME')
        time_list=time_str.split(' ')
        return Time(int(time_list[0]),time_list[1][0])
    
    def set_positions_simple(self,Xpositions,Ypositions,Zpositions=[]):
        """ prepare the controller with arbitrary positions
        Parameters
        ----------
        Xpositions: list of the X positions (instances of Position)
        Ypositions: list of the Y positions (instances of Position)
        Zpositions: list of the Z positions (instances of Position)
        """    
        Nx=len(Xpositions)
        Ny=len(Ypositions)
        Nz=len(Zpositions)
        
        self.write_command('ARBWF {:d} {:d} {:d}'.format(Nx,Ny,Nz))
        
        for xpos in Xpositions:
            self.write_command('ADDPX {:f}{:s}'.format(xpos.pos,xpos.unit))
        for ypos in Ypositions:
            self.write_command('ADDPY {:f}{:s}'.format(ypos.pos,ypos.unit))
        for zpos in Zpositions:
            self.write_command('ADDPZ {:f}{:s}'.format(zpos.pos,zpos.unit))
            
    def run_simple(self):
        self.write_command('RUNWF')
            
    def set_positions_arbitrary(self,positions):
        """ prepare the controller with arbitrary positions
        Parameters
        ----------
        positions: list of 2 lists
            containing respectively the X positions (instances of Position)
            and the Y positions
        """    
        Npoints=len(positions[0])
        self.write_command('ARB3D {:d}'.format(Npoints))
        
        for ind_pos in range(Npoints):
            self.write_command('ADD3D {:f}{:s} {:f}{:s} {:f}{:s}'.format(positions[0].pos,
                               positions[0].unit,positions[1].pos,positions[1].unit,
                                        0,'u'))
            
    def run_arbitrary(self):
        self.write_command('RUN3D ')
        
    def get_TTL_state(self,port=1):
        if port>4 or port<1:
            raise Exception('Invalid IO port number (1-4)')
        else:
            self._piezo.write('DISIO {:d}'.format(port))
            info=self.get_read()
        return info
    
    def set_TTL_state(self,port,axis,IO='disabled',ttl_options=dict(slope='rising',type='start',ind_start=0,ind_stop=0)):
        """ define a given TTL input/output
        Parameters
        ----------
        port: int between 1 and 4
        axis: str either ('X', 'Y' or 'Z')
        IO: str
            either 'disabled', 'input' or 'output'
        ttl_options: dict
            containing the keys:
                slope: str either 'rising' or 'falling' (valid only in 'input' IO mode)
                type: str either 'start', 'end', 'given_step' or 'gate_step' (valid only in 'output' IO mode)
                ind_start: step number to start the TTL (valid for given and gate mode)
                ind_stop: step number to stop the gate (valid for gate mode)
        """
        axes=['X','Y','Z']
        ind_axis=axes.index(axis)+1
        if IO=='disabled':
            self.write_command('CHAIO {:d}{:s}'.format(port,IO[0]))
        elif IO=='input':
            self.write_command('CHAIO {:d}{:s}{:d}{:s}'.format(port,IO[0],ind_axis,ttl_options['slope'][0]))
        elif IO=='output':
            if ttl_options['type']=='start':
                self.write_command('CHAIO {:d}{:s}{:d}{:s}'.format(port,'o',ind_axis,'s'))
            elif ttl_options['type']=='end':
                self.write_command('CHAIO {:d}{:s}{:d}{:s}'.format(port,'o',ind_axis,'e'))
            elif ttl_options['type']=='given_step':
                self.write_command('CHAIO {:d}{:s}{:d}{:s}{:d}'.format(port,'o',ind_axis,'n',ttl_options['ind_start']))
            elif ttl_options['type']=='gate_step':
                self.write_command('CHAIO {:d}{:s}{:d}{:s}{:d}-{:d}'.format(port,'o',ind_axis,'g',ttl_options['ind_start'],ttl_options['ind_stop']))

        else:
            raise Exception('Not valid IO type for TTL')
    
    
    
    
    
    
    