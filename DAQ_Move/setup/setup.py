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

#Check and install setuptools if needed
ez_setup.use_setuptools()
sip_setup()
setup(
	  #Metadata informations
	  name='DAQ_Move',
	  version='1.0',
	  description='CEMES DAQ Move Distribution',
	  author='Sebastien Weber',
	  author_email='sebastien.weber@cemes.fr',
	  url='https://github.com/CEMES-CNRS',

	  #internal requirement (from standard python dist)
	  requires=['sys','enum','os','collections','decimal','xml'],

	  #build local dependancies from source directory
	  package_dir={"PyMoDAQ":"../.."},
	  py_modules= [ 'PyMoDAQ.DAQ_Move.DAQ_Move_GUI',
					'PyMoDAQ.DAQ_Move',
					'PyMoDAQ.DAQ_Move.DAQ_Move_main',
					'PyMoDAQ.DAQ_Move.hardware',
					'PyMoDAQ.DAQ_Utils.custom_parameter_tree',
					'PyMoDAQ.DAQ_Utils.DAQ_utils',
					'PyMoDAQ.DAQ_Utils.hardware.piezoconcept.piezoconcept',
					'PyMoDAQ.DAQ_Utils.plotting.QLED.qled',
					'PyMoDAQ.QtDesigner_Ressources',
					'PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc'],

	  #build dependancies from Pypi and given links
	  install_requires=['PyQt5>=5.5.1',
						'numpy>=1.11.3',
						'pyqtgraph>=0.10.0',
						'easydict>=1.7',
						'datetime',
						'pathlib>=1.0.1',
						'pyvisa>=1.9.0',
						'clr',
						'pyserial>=3.2.1'],
	  dependency_links=['https://sourceforge.net/projects/pyqt/files/sip/',
	  					'https://github.com/pyqtgraph/pyqtgraph.git',
	  					'https://github.com/makinacorpus/easydict.git',
	  					'https://github.com/pyserial/pyserial'
	  					] 

	)