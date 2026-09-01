
import os
import gc
import pytest



def _cleanup_qt_core():
    """
    Dynamically detects the active Qt backend in the current matrix run
    and aggressively flushes/destroys remaining C++ environments.
    """
    # Supported Qt backends across the testing matrix
    backends = ['PySide6', 'PyQt6', 'PyQt5']

    for backend in backends:
        try:
            # Dynamically import the core module of the active backend
            mod = __import__(f"{backend}.QtCore", fromlist=["QCoreApplication"])
            app = mod.QCoreApplication.instance()

            if app is not None:
                # Flush any pending events or delayed signals in the main event loop
                app.processEvents()

                # Attempt to safely close and destroy lingering UI widgets (ParameterTrees, Windows, etc.)
                try:
                    widgets_mod = __import__(f"{backend}.QtWidgets", fromlist=["QApplication"])
                    for widget in widgets_mod.QApplication.topLevelWidgets():
                        if hasattr(widget, 'close'):
                            widget.close()
                        if hasattr(widget, 'deleteLater'):
                            widget.deleteLater()  # Schedule full C++ memory deletion

                    # Process the deleteLater events immediately while the loop is still alive
                    app.processEvents()
                except Exception:
                    pass

                # Signal the application loop to quit and remove the reference
                app.quit()
                del app
                break  # Stop checking once the active backend is processed
        except ImportError:
            continue


@pytest.fixture(autouse=True)
def per_test_cleaner():
    """
    Runs automatically after EVERY single test case.
    Prevents the 'snowball effect' where lingering references trigger random crashes mid-suite.
    """
    yield
    # Force immediate garbage collection of temporary domain models and parameters
    gc.collect()
    try:
        _cleanup_qt_core()
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    """
    Pytest lifecycle hook executed right BEFORE the coverage report is processed.
    Breaks global registries that pytest-cov would otherwise trap in memory.
    """
    try:
        from pyqtgraph.parametertree import Parameter
        # Clear pyqtgraph's global dictionary cache containing your custom registered parameters
        Parameter.PARAM_TYPES = {}
    except Exception:
        pass

    # Flush memory before coverage locks the thread context
    gc.collect()
    _cleanup_qt_core()


def pytest_unconfigure(config):
    """
    Final ultimate safety net executed right before the Python interpreter exits.
    Ensures PySide/PyQt and Python close down in an orderly chronological sequence.
    """
    _cleanup_qt_core()
    gc.collect()
