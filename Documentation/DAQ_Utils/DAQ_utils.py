from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject,pyqtSignal, QSize, QEvent
import numpy as np
import datetime
from pathlib import Path

def odd_even(x):
    """
    odd_even tells if a number is odd (return True) or even (return False)
    
    Parameters
    ----------
    x: the integer number to test
      
    Returns
    -------
    bool : boolean
    """
    if int(x)%2==0:
        bool=False
    else:
        bool=True
    return bool 

def set_scan_spiral(start_axis1,start_axis2,rmax,rstep):
    """Set a spiral scan of a 0D Data aquisition.

        =============== ========== ==========================================
        **Parameters**   **Type**   **Description**
        *start_axis1*    int        The starting value of the first sequence
        *start_axis2*    int        The starting value of the second sequence  
        *rmax*           int        The end point
        *rstep*          int        The value of one step
        =============== ========== ==========================================

        Returns
        -------
        (int,int list,int list,scalar list) tuple
            The tuple containing :
             * the number of steps
             * the first axis
             * the second axis
             * the positions int values

        Examples
        --------
        .. doctest::

            >>> import DAQ_utils as Du
            >>> start_axis1,start_axis2=1,1
            >>> rmax=2
            >>> rstep=1
            >>> spiral_scan=Du.set_scan_spiral(start_axis1,start_axis2,rmax,rstep)
            >>> print(spiral_scan[0])       #The number of step
            25                                  
            >>> print(spiral_scan[1])       #The first distributed axis
            [-1  0  1  2  3]
            >>> print(spiral_scan[2])       #The second distributed axis
            [-1  0  1  2  3]
            >>> print(spiral_scan[3])       #The positions scalar list computed
            [[1, 1], [2, 1], [2, 2], [1, 2], [0, 2],
            [0, 1], [0, 0], [1, 0], [2, 0], [3, 0],
            [3, 1], [3, 2], [3, 3], [2, 3], [1, 3],
            [0, 3], [-1, 3], [-1, 2], [-1, 1], [-1, 0],
            [-1, -1], [0, -1], [1, -1], [2, -1], [3, -1]]
    """
    positions_int=[[0,0]]
    ind=0
    flag=True

    Nlin=np.rint(rmax/rstep)


    while flag:
        if odd_even(ind):
            step=1
        else:
            step=-1
        if flag:
            for ind_step in range(ind):
                positions_int.append([positions_int[-1][0]+step , positions_int[-1][1] ])
                if (positions_int[-1][0]>=Nlin and positions_int[-1][1]<=-Nlin):
                    flag=False
                    break
        if flag:
            for ind_step in range(ind):
                positions_int.append([positions_int[-1][0] , positions_int[-1][1]+step ])
                if (positions_int[-1][0]>=Nlin and positions_int[-1][1]<=-Nlin):
                    flag=False
                    break
        ind+=1

    axis_1=np.unique([pos[0]*rstep+start_axis1 for pos in positions_int])
    axis_2=np.unique([pos[1]*rstep+start_axis2 for pos in positions_int])

    positions=[[pos[0]*rstep+start_axis1,pos[1]*rstep+start_axis2] for pos in positions_int]
    Nsteps=len(positions)
    return Nsteps,axis_1,axis_2,positions

def linspace_step(start,stop,step):
    """
        Compute a regular linspace_step distribution from start to stop values.

        =============== =========== ======================================
        **Parameters**    **Type**    **Description**
        *start*            scalar      the starting value of distribution
        *stop*             scalar      the stopping value of distribution
        *step*             scalar      the length of a distribution step
        =============== =========== ======================================

        Returns
        -------

        scalar array
            The computed distribution axis as an array.

        Examples
        --------
        >>> import DAQ_utils as Du
        >>> import numpy as np
        >>>    #arguments initializing
        >>> start=0
        >>> stop=5
        >>> step=0.25
        >>> linspace_distribution=Du.linspace_step(start,stop,step)
        >>> print(linspace_distribution)
        >>>    #computed distribution
        [ 0.    0.25  0.5   0.75  1.    1.25  1.5   1.75  2.    2.25  2.5   2.75
          3.    3.25  3.5   3.75  4.    4.25  4.5   4.75  5.  ]        
    """
    tmp=start
    out=np.array([tmp])    
    if step>=0:
        while (tmp<=stop):
            tmp=tmp+step
            out=np.append(out,tmp)
    else:
        while (tmp>=stop):
            tmp=tmp+step
            out=np.append(out,tmp)
    return out[0:-1]



def set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis_2,back_and_force=False):
    """
        Set a linear scan of a 0D Data aquisition.
        The positions scalar list is computed by a Cartesian product of the first distributed axis and the second one.
        
        The result size is composed by :
        * a single integer representing the number of step
        * a n items integer array representing the first distributed axis
        * a k items integer array representing the second distributed axis
        * a n*k items containing the combinaisons of the first and the second axis distribution.

        ================ ========== =============================================
        **Parameters**    **Type**   **Description**
        *start_axis1*     scalar     The starting value of the first sequence
        *start_axis2*     scalar     The starting value of the second sequence
        *stop_axis1*      scalar     The end point of the first sequence
        *stop_axis2*      scalar     The end point of the second sequence
        *step_axis1*      float      The value of one step of the first sequence
        *step_axis_2*     float      The value of one step of the second sequence
        *back_and_force*  boolean    ???
        ================ ========== =============================================


        Returns
        -------
        (int,float list,float list,scalar list) tuple
            The tuple containing:
             * The number of step
             * The first distributed axis
             * The second distributed axis
             * The positions scalar list computed

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> start_axis1,start_axis2=1,1
            >>> stop_axis1,stop_axis2=3,3
            >>> step_axis1,step_axis2=1,1
            >>> linear_scan=Du.set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis2)
            >>> print(linear_scan[0])       #The number of step
            9
            >>> print(linear_scan[1])       #The first distributed axis
            [1 2 3]
            >>> print(linear_scan[2])       #The second distributed axis
            [1 2 3]
            >>> print(linear_scan[3])       #The positions scalar list computed
            [[1, 1], [1, 2], [1, 3], [2, 1], [2, 2], [2, 3], [3, 1], [3, 2], [3, 3]]
    """
    axis_1=linspace_step(start_axis1,stop_axis1,step_axis1)
    axis_2=linspace_step(start_axis2,stop_axis2,step_axis_2)
    positions=[]
    for pos1 in axis_1:
        if back_and_force:
            positions.extend([[pos1,pos2] for pos2 in axis_2[-1::-1]])
        else:
            positions.extend([[pos1,pos2] for pos2 in axis_2])

    Nsteps=len(positions)
    return Nsteps,axis_1,axis_2,positions


def find_part_in_path_and_subpath(base_dir,part='',create=False):
    """
        Find path from part time.

        =============== ============ =============================================
        **Parameters**  **Type**      **Description**
        *base_dir*      Path object   The directory to browse
        *part*          string        The date of the directory to find/create
        *create*        boolean       Indicate the creation flag of the directory
        =============== ============ =============================================

        Returns
        -------
        Path object
            found path from part

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> import pathlib as pl
            >>> base_dir=pl.Path("") #Getting the current path
            >>> print(base_dir)
            .
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2018",True)
            >>> print(path)       #Path of created directory "2018"
            2018
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2017",False)
            >>> print(path)       #Path is none since "2017" dir doesn't exist
            None
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2018",False)
            >>> print(path)       #Path of directory "2018"
            2018
    """
    found_path=None
    if part in base_dir.parts: #check if current year is in the given base path
        if base_dir.name==part:
            found_path=base_dir
        else:
            for ind in range(len(base_dir.parts)):
                tmp_path=base_dir.parents[ind]
                if tmp_path.name==part:
                    found_path=base_dir.parents[ind]
                    break
    else:#if not check if year is in the subfolders
        subfolders_year_name=[x.name for x in base_dir.iterdir() if x.is_dir()]
        subfolders_found_path=[x for x in base_dir.iterdir() if x.is_dir()]
        if part not in subfolders_year_name:
            if create:
                found_path=base_dir.joinpath(part)
                found_path.mkdir()
        else:
            ind_path=subfolders_year_name.index(part)
            found_path=subfolders_found_path[ind_path]
    return found_path

def set_current_scan_path(base_dir,base_name='Scan',update_h5=False):
    """
        Set the path of the current scan and create associated directory tree.
        As default :

        Year/Date/Dataset_Date_ScanID/ScanID


        =============== ============ =====================================
        **Parameters**  **Type**      **Description**
        base_dir        Path object   The base directory
        base_name       string        Name of the current scan
        update_h5       boolean       1/0 to update the associated h5 file
        =============== ============ =====================================

        Returns
        -------
        scan_path 
            indexed base_name, new folder indexed from base name at the day

        See Also
        --------
        DAQ_utils.find_part_in_path_and_subpath

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> import pathlib as pl
            >>> base_dir=pl.Path("") #Getting the current path
            >>>
            >>> current_scan_path=Du.set_current_scan_path(base_dir)
            >>>  #Function call with default name
            >>> print(current_scan_path[0])       #The full scan path
            2018\20180424\Dataset_20180424_000\Scan000
            >>> print(current_scan_path[1])       #The indexed base name
            Scan000
            >>> print(current_scan_path[2])       #The dataset_path
            2018\20180424\Dataset_20180424_000
            >>>
            >>> current_scan_path=Du.set_current_scan_path(base_dir,'Specific name')
            >>> #Function call with a specific name
            >>> print(current_scan_path[0])       #The full scan path
            2018\20180424\Dataset_20180424_000\Specific name000
            >>> print(current_scan_path[1])       #The indexed base name
            Specific name000
            >>> print(current_scan_path[2])       #The dataset_path
            2018\20180424\Dataset_20180424_000
    """
    base_dir=Path(base_dir)
    date=datetime.date.today()

    year_path=find_part_in_path_and_subpath(base_dir,part=str(date.year),create=True)# create directory of the year if it doen't exist and return it
    day_path=find_part_in_path_and_subpath(year_path,part=date.strftime('%Y%m%d'),create=True)# create directory of the day if it doen't exist and return it

    date=datetime.date.today()
    dataset_base_name=date.strftime('Dataset_%Y%m%d')
    dataset_paths=sorted([path for path in day_path.glob(dataset_base_name+"*") if path.is_dir()])
    if dataset_paths==[]:
        ind_dataset=0
    else:
        if update_h5:
            ind_dataset=int(dataset_paths[-1].name.partition(dataset_base_name+"_")[2])+1
        else:
            ind_dataset=int(dataset_paths[-1].name.partition(dataset_base_name+"_")[2])
    dataset_path=find_part_in_path_and_subpath(day_path,part=dataset_base_name+"_{:03d}".format(ind_dataset),create=True)

    scan_paths=sorted([path for path in dataset_path.glob(base_name+'*') if path.is_dir()])
    if scan_paths==[]:
        ind_scan=0
    else:
        if list(scan_paths[-1].iterdir())==[]:
            ind_scan=int(scan_paths[-1].name.partition(base_name)[2])
        else:
            ind_scan=int(scan_paths[-1].name.partition(base_name)[2])+1
    scan_path=find_part_in_path_and_subpath(dataset_path,part=base_name+'{:03d}'.format(ind_scan),create=True)
    return scan_path,base_name+'{:03d}'.format(ind_scan),dataset_path


def select_file(start_path=None,save=True, ext='h5'):
    """
        Save or open a file with Qt5 file dialog, to be used within an Qt5 loop.

        =============== ======================================= ===========================================================================
        **Parameters**     **Type**                              **Description**

        *start_path*       Path object or str or None, optional  the path Qt5 will open in te dialog
        *save*             bool, optional                        * if True, a savefile dialog will open in order to set a savefilename
                                                                 * if False, a openfile dialog will open in order to open an existing file
        *ext*              str, optional                         the extension of the file to be saved or opened
        =============== ======================================= ===========================================================================

        Returns
        -------
        Path object
            the Path object pointing to the file

        Examples
        --------
        >>>from PyQt5 import QtWidgets
        >>>from PyMoDAQ.DAQ_Utils.DAQ_utils import select_file
        >>>import sys
        >>>app = QtWidgets.QApplication(sys.argv)
        >>>    #Open a save windows
        >>>select_file(start_path="C:/test",save=False,ext='h5')
        >>>sys.exit(app.exec_())

    """
    if not save:
        if type(ext)!=list:
            ext=[ext]
        filter="Data files ("
        for ext_tmp in ext:
            filter+='*.'+ext_tmp+" "
        filter+=")"
    if start_path is not None:
        if type(start_path) is not str:
            start_path=str(start_path)
    if save:
        fname = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a .'+ext+' file name',start_path,ext+" file (*."+ext+")")
    else:
        fname=QtWidgets.QFileDialog.getOpenFileName(None, 'Select a file name',start_path,filter)

    fname=fname[0]
    if not( not(fname)): #execute if the user didn't cancel the file selection
        fname=Path(fname)
        if save:
            parent=fname.parent
            filename=fname.stem
            fname=parent.joinpath(filename+"."+ext) #forcing the right extension on the filename
    return fname #fname is a Path object

def find_index(x,threshold):
    """
    find_index finds the index ix such that x(ix) is the closest from threshold
    
    Parameters
    ----------
    x : vector
    threshold : list of scalar

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    
    Examples
    --------
    >>> import array_manipulation as am
    >>> import numpy as np
    >>>    #vector creation
    >>> x_vector=np.array([1,2,3])
    >>> index=am.find_index(x_vector,4)
    >>>    #the nearest index from threshold
    >>> print(index)
    >>>    #ix=2, x[2]=3  , threshold=4
    [(2, 3)]
    >>>
    >>> x_vector=np.array([1,2,3,4,5,6,7,8,9,10])
    >>> index=am.find_index(x_vector,[3.8,7.5,12.])
    >>>    #the nearest indexs from threshold list [3.8,7.5,12.]
    >>> print(index)
    >>>    #ix0=3, x[3]=4  , threshold=3.8
    >>>    #ix1=6, x[6]=7  , threshold=7.5
    >>>    #ix2=9, x[9]=10 , threshold=12.0
    [(3, 4), (6, 7), (9, 10)]
    """
        
    if np.isscalar(threshold):
        threshold=[threshold]
    out=[]
    for value in threshold:
        ix=int(np.argmin(np.abs(x-value))) 
        out.append((ix,x[ix]))
    return out

def gauss1D(x,x0,dx,n=1):
    """
    compute the gaussian function along a vector x, centered in x0 and with a
    FWHM i intensity of dx. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian

    =============== =========== ============================================================
    **Parameters**    **Type**    **Description**
    *x*               vector      vector
    *x0*              float       the central position of the gaussian
    *dx*              float       the FWHM of the gaussian
    *n*               float       define hypergaussian, n=1 by default for regular gaussian
    =============== =========== ============================================================     

    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis

    Examples
    --------
    >>> import DAQ_utils as Du
    >>> import numpy as np                
    >>> x=np.array([0,1,2,3,4])            #argument initializing
    >>> x0=2
    >>> dx=0.5
    >>> gaussian_distribution=Du.gauss1D(x,x0,dx)
    >>> print(gaussian_distribution)       #The computed gaussian distribution
    [  2.32830644e-10   3.90625000e-03   1.00000000e+00   3.90625000e-03
       2.32830644e-10]    
    """
    out=np.exp(-2*np.log(2)**(1/n)*(((x-x0)/dx))**(2*n))
    return out

def gauss2D(x,x0,dx,y,y0,dy,n=1):
    """
    compute the 2D gaussian function along a vector x, centered in x0 and with a
    FWHM in intensity of dx and smae along y axis. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian

    =============== =========== ===========================================================
    **Parameters**    **Type**    **Description**
    *x*               vector      the x_axis
    *x0*              float       the central position of the gaussian on x_axis
    *dx*              float       the FWHM of the gaussian on x_axis
    *y*               vector      the y_axis
    *y0*              float       the central position of the gaussian on y_axis
    *dy*              float       the FWHM of the gaussian on y_axis
    *n*               float       define hypergaussian, n=1 by default for regular gaussian 
    =============== =========== ===========================================================

    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis

    Examples
    --------
    >>> import DAQ_utils as Du
    >>> import numpy as np
    >>>    #arguments initializing
    >>> x,y=np.array([0,1,2,3,4]),np.array([0,1,2,3,4])
    >>> x0,y0=2,2
    >>> dx,dy=0.5,0.5
    >>> gaussian_distribution=Du.gauss2D(x,x0,dx,y,y0,dy)
    >>>    #the computed 2d gaussian distribution
    >>> print(gaussian_distribution)
    [[  5.42101086e-20   9.09494702e-13   2.32830644e-10   9.09494702e-13
        5.42101086e-20]
     [  9.09494702e-13   1.52587891e-05   3.90625000e-03   1.52587891e-05
        9.09494702e-13]
     [  2.32830644e-10   3.90625000e-03   1.00000000e+00   3.90625000e-03
        2.32830644e-10]
     [  9.09494702e-13   1.52587891e-05   3.90625000e-03   1.52587891e-05
        9.09494702e-13]
     [  5.42101086e-20   9.09494702e-13   2.32830644e-10   9.09494702e-13
        5.42101086e-20]]   
    """
    out=np.transpose(np.outer(gauss1D(x,x0,dx,n),gauss1D(y,y0,dy,n)))
    return out
    
def ftAxis_time(Npts,time_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    =============== =========== ===========================================================================
    **Parameters**    **Type**    **Description**
    *Npts*            int          A number of points defining the length of both grids
    *time_max*       float         The maximum circular frequency in the spectral domain. its unit defines
                                   the temporal units. ex: omega_max in rad/fs implies time_grid in fs
    =============== =========== ===========================================================================

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT

    time_grid : vector
      The temporal axis of the FFT

    Example
    -------
    >>> (omega_grid, time_grid)=ftAxis(Npts,omega_max)
    ...
    """
    dT=time_max/Npts
    omega_max=(Npts-1)/2*2*np.pi/time_max
    omega_grid = np.linspace(-omega_max,omega_max,Npts)
    time_grid = dT*np.linspace(-(Npts-1)/2,(Npts-1)/2,Npts)
    return omega_grid, time_grid
    
    
def ft(x,dim=0):
    out=np.fft.fftshift(np.fft.fft(np.fft.fftshift(x,axes=dim),axis=dim),axes=dim)
    return out
    
def ift(x,dim=0):
    out=np.fft.fftshift(np.fft.ifft(np.fft.fftshift(x,axes=dim),axis=dim),axes=dim)
    return out   



class ThreadCommand(object):
    """ | Micro class managing the thread commands.
        | 
        | A thread command is composed of a string name defining the command to execute and an attribute list splitable making arguments of the called function.

        =============== =============
        **Attributes**  **Type**
        *command*       string
        *attributes*    generic list
        =============== =============

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> thread_command_ex=Du.ThreadCommand("The command name",
            ... ["differents","attributes","here"])
            >>>   #The thread command memory location
            >>> print(thread_command_ex)
            <DAQ_utils.ThreadCommand object at 0x000000000A390B38>
            >>>   #A command name
            >>> print(thread_command_ex.command)
            The command name
            >>>   #the attributes treated as parameter once the command treated
            >>> print(thread_command_ex.attributes)
            ['differents', 'attributes', 'here']
            >>>   #Attributes type is generic
            >>> thread_command_ex=Du.ThreadCommand("The command name",
            ... [10,20,30,40,50])
            >>>   #A different memory location
            >>> print(thread_command_ex)
            <DAQ_utils.ThreadCommand object at 0x0000000005372198>
            >>>   #A command name
            >>> print(thread_command_ex.command)
            The command name
            >>>   #With new attributes
            >>> print(thread_command_ex.attributes)
            [10, 20, 30, 40, 50]

    """
    def __init__(self,command="",attributes=[]):
        self.command=command
        self.attributes=attributes
