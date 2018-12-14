from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

setup(
    ext_modules=cythonize([Extension("picoscope_5000A",["picoscope_5000A.pyx"],
            include_dirs=["C://Program Files/Pico Technology/SDK/inc"],
            library_dirs=["C://Program Files/Pico Technology/SDK/lib"],
            libraries=["ps5000a"])])
)