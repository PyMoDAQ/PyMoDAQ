import distutils.dir_util
from distutils.command import build
import os, sys, re
try:
    import setuptools
    from setuptools import setup, find_packages
    from setuptools.command import install
except ImportError:
    sys.stderr.write("Warning: could not import setuptools; falling back to distutils.\n")
    from distutils.core import setup
    from distutils.command import install

from pymodaq.version import get_version

with open('README.rst') as fd:
    long_description = fd.read()

setupOpts = dict(
    name='pymodaq',
    description='Modular Data Acquisition with Python',
    long_description=long_description,
    license='MIT',
    url='http://pymodaq.cnrs.fr',
    author='Sébastien Weber',
    author_email='sebastien.weber@cemes.fr',
    classifiers = [
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: CeCILL-B Free Software License Agreement (CECILL-B)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
        ],)

def listAllPackages(pkgroot):
    path = os.getcwd()
    n = len(path.split(os.path.sep))
    subdirs = [i[0].split(os.path.sep)[n:] for i in os.walk(os.path.join(path, pkgroot)) if '__init__.py' in i[2]]
    return ['.'.join(p) for p in subdirs]


allPackages = (listAllPackages(pkgroot='pymodaq')) #+
               #['pyqtgraph.'+x for x in helpers.listAllPackages(pkgroot='examples')])



def get_packages():

    packages=find_packages()
    for pkg in packages:
        if 'hardware.' in pkg:
            packages.pop(packages.index(pkg))
    return packages

allPackages = get_packages()



setup(
    version=get_version(),
     #cmdclass={'build': Build,},
    #           'install': Install,
    #           'deb': helpers.DebCommand,
    #           'test': helpers.TestCommand,
    #           'debug': helpers.DebugCommand,
    #           'mergetest': helpers.MergeTestCommand,
    #           'style': helpers.StyleCommand},
    packages=allPackages,
    #package_dir={'examples': 'examples'},  ## install examples along with the rest of the source
    package_data={},
    entry_points={'console_scripts': ['dashboard=pymodaq.dashboard:main',
                                      'daq_scan=pymodaq.daq_scan:main',
                                      'daq_logger=pymodaq.daq_logger:main',
                                      'daq_viewer=pymodaq.daq_viewer.daq_viewer_main:main',
                                      'daq_move=pymodaq.daq_move.daq_move_main:main',
                                      'h5browser=pymodaq.h5browser:main'],
                  },
    python_requires='>=3.6, <3.8',
    install_requires=[
        'numpy',
        'scipy',
        'pyqtgraph==0.10',
        'easydict',
        #'pyqt5',
        'tables',
        'pymodaq_plugins>=2.0.1',
        'pymodaq_pid_models>=0.0.2',
	    'simple_pid',
        'python-dateutil',
        'packaging',
        'SQLAlchemy-Utils==0.36.6', #this is so that the check for database existence doesn't crash anymore, see pull request 463
        'toml',
        'pymodaq_plugin_manager',

        ],
    include_package_data=True,
    **setupOpts
)

