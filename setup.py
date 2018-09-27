import os

def get_root():
	if (os.name=='nt'):  #Windows users
		return os.popen('cd').read()
	else:				#Posix users
		return os.popen('pwd').read()

root=get_root()
choice=''

os.system('python DAQ_Analysis\setup\setup.py install')
os.system('python DAQ_Measurement\setup\setup.py install')
os.system('python DAQ_Metheor\setup\setup.py install')
os.system('python DAQ_Move\setup\setup.py install')
os.system('python DAQ_Scan\setup\setup.py install')
os.system('python DAQ_Viewer\setup\setup.py install')
os.system('python DAQ_Analysis\setup\dep_setup.py install')


