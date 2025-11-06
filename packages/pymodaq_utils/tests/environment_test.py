import os, sys
import pytest


from pymodaq_utils.environment import guess_virtual_environment, PythonEnvironment


POSSIBLE_VENV_VARIABLES = ['VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'PYENV_VERSION', 'TOX_ENV_NAME']
class TestGuessVirtualEnvironment:

    @pytest.mark.parametrize("var", POSSIBLE_VENV_VARIABLES)
    def test_from_environment_var(self, monkeypatch, var):
        venv_name = "if_your_environment_is_called_like_that_you_should_probably_change_it"

        # set one of the possible environment variable to the var name value
        # and remove the others
        monkeypatch.setenv(var, os.path.join("/home/./folder/", venv_name))
        for other in  [o for o in POSSIBLE_VENV_VARIABLES if o != var]:
            monkeypatch.delenv(other, raising=False)   
        
        assert guess_virtual_environment() == venv_name


    def test_from_prefix(self, monkeypatch):
        venv_name = "if_your_environment_is_called_like_that_you_should_probably_change_it"
        for var in POSSIBLE_VENV_VARIABLES:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setattr(sys, "prefix", os.path.join("/home/./folder/", venv_name))
        assert guess_virtual_environment() == venv_name


    def test_unknown(self, monkeypatch):
        for var in POSSIBLE_VENV_VARIABLES:
            monkeypatch.delenv(var, raising=False)   
        
        monkeypatch.setattr(sys, "prefix", sys.base_prefix)
        assert guess_virtual_environment() == 'unknown'

class TestPythonEnvironment:
    def test_empty_init(self):
        e = PythonEnvironment()
        assert len(e._packages) == 0

    def test_equality(self):
        package_list = ['package_one==0.0.1', 'package_two==0.0.2', 'package_three==0.0.3', 'package_four==0.0.4', 'package_five==0.0.5']
        e1 = PythonEnvironment()
        e1.extend(package_list)

        e2 = PythonEnvironment()
        e2.extend(package_list)
        assert e1 == e2

    def test_different(self):
        package_list = ['package_one==0.0.1', 'package_two==0.0.2', 'package_three==0.0.3', 'package_four==0.0.4', 'package_five==0.0.5']
        e1 = PythonEnvironment()
        e1.extend(package_list[2:])
        e2 = PythonEnvironment()
        e2.extend(package_list[:3])
        assert e1 != e2

        e1 = PythonEnvironment()
        e1.extend(package_list)
        package_list[0] = 'package_one==0.0.2'
        e2 = PythonEnvironment()
        e2.extend(package_list)
        assert e1 != e2
        

    def test_freeze(self):
        e1 = PythonEnvironment.from_freeze()
        e2 = PythonEnvironment.from_freeze()

        assert e1 == e2, "Two pip freeze in a row don't return the same environment. Ensure no pip install are running."