#!/usr/bin/env python

#win distribution : bdist_wininst

# @author  CABOS Matthieu
# @release 30/04/2018

from setuptools import setup
import os
import ez_setup
import os

def sip_setup():
	try:
		os.system('pip install wheel')
		os.system('pip3 install -e ../Libraries_packages/sip/sip-4.19.8-cp35-none-win_amd64.whl')
	except:
		print("pip3 needed to perform setup. Please download and install.")
		exit(0)

def tables_setup():
	try:
		os.system('pip install tables>=3.3.0')
	except:
		print("tables module needed to perform setup; Please download and install tables.")
		exit(0)

#Check and install setuptools if needed
ez_setup.use_setuptools()
sip_setup()
tables_setup()
setup(
	  #Metadata informations
	  name='DAQ_Scan',
	  version='1.0',
	  description='CEMES DAQ Scan Distribution',
	  author='Sebastien Weber',
	  author_email='sebastien.weber@cemes.fr',
	  url='https://github.com/CEMES-CNRS',

	  #internal requirement (from standard python dist)
	  requires=['sys','os','datetime','pickle','enum'],

	  #build dependancies from Pypi and given links
	  install_requires=['numpy>=1.11.3',
	  					'pyqtgraph>=0.10.0',
	  					'easydict>=1.7',
	  					#'tables>=3.3.0',
	  					'PyQt5>=5.5.1',
	  					'pandas>=0.19.2',
	  					'bitstring>=3.1.5',
	  					'pathlib>=1.0.1',
	  					'clr>=1.0.3',
	  					'pyvisa>=1.9',
	  					'pyserial>=3.2.1',
	  					'matplotlib>=2.0.0',
	  					'scipy>=0.18.1'],
	  dependency_links=['https://github.com/pyqtgraph/pyqtgraph.git',
	  					'https://github.com/makinacorpus/easydict.git',
	  					'https://sourceforge.net/projects/pytables/files/pytables/',
	  					'https://github.com/pyvisa/pyvisa.git',
	  					'https://github.com/pyserial/pyserial.git'],

	  #build local dependancies from source directory
	  package_dir={"PyMoDAQ":"../.."},
	  py_modules = ['PyMoDAQ.DAQ_Scan',
	  				'PyMoDAQ.DAQ_Scan.DAQ_Scan_main',
	  				'PyMoDAQ.DAQ_Scan.GUI.DAQ_Scan_GUI',
					'PyMoDAQ.DAQ_Move.hardware',
					'PyMoDAQ.DAQ_Utils.DAQ_utils',
					'PyMoDAQ.DAQ_Utils.custom_parameter_tree',
					'PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor',
					'PyMoDAQ.DAQ_Move.DAQ_Move_main',
					'PyMoDAQ.DAQ_Viewer.DAQ_viewer_main',
					'PyMoDAQ.DAQ_Move',
					'PyMoDAQ.DAQ_Viewer',
					'PyMoDAQ.DAQ_Utils.plotting.QLED.qled',
					'PyMoDAQ.DAQ_Utils',
					'PyMoDAQ.DAQ_Move.DAQ_Move_GUI',
					'PyMoDAQ.QtDesigner_Ressources',
					'PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc']
)