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



with open('README.md') as fd:
    long_description = fd.read()

setupOpts = dict(
    name='pymodaq',
    description='Modular Data Acquisition with Python',
    long_description=long_description,
    license='MIT',
    url='',
    author='Sébastien Weber',
    author_email='sebastien.weber@cemes.fr',
    classifiers = [
        "Programming Language :: Python :: 3",
        #"Development Status :: 1 - Beta",
        "Environment :: Other Environment",
        #"Intended Audience :: Association/Organisation",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
        ],)


class Build(build.build):
    """
    * Clear build path before building
    """

    def run(self):
        global path

        ## Make sure build directory is clean
        buildPath = os.path.join(path, self.build_lib)
        if os.path.isdir(buildPath):
            distutils.dir_util.remove_tree(buildPath)


        ret = build.build.run(self)



setup(
    version='0.0.1',
    # cmdclass={'build': Build,},
    #           'install': Install,
    #           'deb': helpers.DebCommand,
    #           'test': helpers.TestCommand,
    #           'debug': helpers.DebugCommand,
    #           'mergetest': helpers.MergeTestCommand,
    #           'style': helpers.StyleCommand},
    packages=[],#find_packages(),
    #package_dir={'examples': 'examples'},  ## install examples along with the rest of the source
    package_data={},
    install_requires = [
        'numpy',
        'pyqtgraph==0.10',
        'bitstring',
        'easydict',
        #'pyqt5',
        'tables',
        ],
    **setupOpts
)

