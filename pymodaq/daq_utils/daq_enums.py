from enum import Enum
from pymodaq.daq_utils.daq_utils import find_index
from pymodaq.daq_utils.daq_utils import my_moment
import numpy as np
from scipy.optimize import curve_fit


class DAQ_Picoscope_range(Enum):
    _10mV=0
    _20mV=1
    _50mV=2
    _100mV=3
    _200mV=4
    _500mV=5
    _1V=6
    _2V=7
    _5V=8
    _10V=9
    _20V=10
    _50V=11
    def names(self):
        names=self.__members__.items()
        return ["+/-"+name[1:] for name, member in self.__members__.items()]



class Items_Lockin_SR830(Enum):
    X=0
    Y=1
    R=2
    Theta=3 
    Channel_1=4
    Channel_2=5
    Aux_In_1=6
    Aux_In_2=7
    Aux_In_3=8
    Aux_In_4=9
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]


class DAQ_type(Enum):
    DAQ0D=0
    DAQ1D=1
    DAQ2D=2

    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]




class DAQ_0DViewer_lockin_type(Enum):
    SR830=0
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]


class Measurement_type(Enum):
    Cursor_Integration=0
    Max=1
    Min=2
    Gaussian_Fit=3
    Lorentzian_Fit=4
    Exponential_Decay_Fit=5
    
    def names(self):
        names=Measurement_type.__members__.items()
        return [name for name, member in names]

    def update_measurement_subtype(self,mtype):
        measurement_gaussian_subitems= ["amp","dx","x0","offset"]
        measurement_laurentzian_subitems= ["alpha","gamma","x0","offset","amplitude"]
        measurement_decay_subitems= ["N0","gamma","offset"]
        measurement_cursor_subitems=["sum","mean","std"]
        variables=", "
        formula=""
        subitems=[]
        if mtype==self.names(self)[0]:#"Cursor integration":
            subitems=measurement_cursor_subitems

        if mtype==self.names(self)[3]:#"Gaussian Fit":
            subitems=measurement_gaussian_subitems
            formula="amp*exp(-2*ln(2)*(x-x0)^2/dx^2)+offset"
            variables=variables.join(measurement_gaussian_subitems)
                
        elif mtype==self.names(self)[4]:#"Lorentzian Fit":
            subitems=measurement_laurentzian_subitems
            variables=variables.join(measurement_laurentzian_subitems)
            formula="alpha/pi*gamma/2/((x-x0)^2+(gamma/2)^2)+offset"
        elif mtype==self.names(self)[5]:#"Exponential Decay Fit":
            subitems=measurement_decay_subitems
            variables=variables.join(measurement_decay_subitems)
            formula="N0*exp(-gamma*x)+offset"
        return [variables,formula,subitems]

    def gaussian_func(self,x,amp,dx,x0,offset):
        return amp * np.exp(-2*np.log(2)*(x-x0)**2/dx**2) + offset

    def laurentzian_func(self,gamma,amp,dx,x0,offset):
        return amp/np.pi * 1/2*gamma /((x-x0)**2+(1/2*gamma)**2) + offset

    def decaying_func(self,x,N0,gamma,offset):
        return N0 * np.exp(-gamma*x)+offset
       
    def update_measurement(self,xmin,xmax,xaxis,data1D,msub_ind):
        try:
            mtype=self.name
            names=self.names()
            boundaries=find_index(xaxis,[xmin,xmax])
            sub_xaxis=xaxis[boundaries[0][0]:boundaries[1][0]]
            sub_data=data1D[boundaries[0][0]:boundaries[1][0]]
            result_measurement=dict(Status=None,datafit=None,xaxis=None)
            
            if mtype==names[0]:#Cursor integration:
                if msub_ind==0:#sum
                    result_measurement['value']=np.sum(sub_data)
                elif msub_ind==1:#mean
                    result_measurement['value']=np.mean(sub_data)
                elif msub_ind==2:#std
                    result_measurement['value']=np.std(sub_data)
                      
            elif mtype==names[1]:#"Max":
                result_measurement['value']=np.max(sub_data)

            elif mtype==names[2]:#"Min":
                result_measurement['value']=np.min(sub_data)

            elif mtype==names[3]:#"Gaussian Fit":
                offset=np.min(sub_data)
                amp=np.max(sub_data)-np.min(sub_data)
                m=my_moment(sub_xaxis,sub_data)
                p0=[amp,m[1],m[0],offset]
                popt, pcov = curve_fit(self.gaussian_func, sub_xaxis, sub_data,p0=p0)
                result_measurement['xaxis']=sub_xaxis
                result_measurement['datafit']=self.gaussian_func(sub_xaxis,*popt)
                result_measurement['value']=popt[msub_ind]
            
            elif mtype==names[4]:#"Lorentzian Fit":
                offset=np.min(sub_data)
                amp=np.max(sub_data)-np.min(sub_data)
                m=my_moment(sub_xaxis,sub_data)
                p0=[amp,m[1],m[0],offset]
                popt, pcov = curve_fit(self.laurentzian_func, sub_xaxis, sub_data,p0=p0)
                result_measurement['xaxis']=sub_xaxis
                result_measurement['datafit']=self.laurentzian_func(sub_xaxis,*popt)
                
                if msub_ind==4:#amplitude
                    result_measurement['value']=popt[0]*2/(np.pi*popt[1])#2*alpha/(pi*gamma)
                else:
                    result_measurement['value']=popt[msub_ind]
            elif mtype==names[5]:#"Exponential Decay Fit":
                offset=min([sub_data[0],sub_data[-1]])
                N0=np.max(sub_data)-offset
                polynome=np.polyfit(sub_xaxis,-np.log((sub_data-0.99*offset)/N0),1)
                p0=[N0,polynome[0],offset]
                popt, pcov = curve_fit(self.decaying_func, sub_xaxis, sub_data,p0=p0)
                self.curve_fitting_sig.emit([True,sub_xaxis,self.decaying_func(sub_xaxis,*popt)])
                result_measurement['xaxis']=sub_xaxis
                result_measurement['datafit']=self.decaying_func(sub_xaxis,*popt)
                result_measurement['value']=popt[msub_ind]


            return (result_measurement)
        except Exception as e:
            result_measurement['Status']=str(e)
            return result_measurement