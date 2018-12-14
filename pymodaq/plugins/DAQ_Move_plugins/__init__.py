import os,fnmatch
import importlib
path=os.path.abspath(__file__)
(path,tail)=os.path.split(path)

files=list();
for file in os.listdir(path):
    if fnmatch.fnmatch(file, "*.py"):
        files.append(file)
        
if '__init__.py' in files:
    files.remove('__init__.py')

__all__=[file[:-3] for file in files]
for mod in __all__:
    try:
        importlib.import_module('.' + mod, 'pymodaq.plugins.daq_move_plugins')
    except Exception as e:
        print("error while trying to import module {:}:{:}".format(mod,str(e)))
        pass
#from PyMoDAQ.plugins.DAQ_Move_plugins import *