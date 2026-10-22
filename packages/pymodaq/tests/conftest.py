
import os
import gc
import pytest
import sys
import time

_gc_start = {}


def _gc_timing(phase, info):  # TEMPORARY diagnostic: long garbage collections (PySide6 CI stalls)
    if phase == 'start':
        _gc_start['t'] = time.perf_counter()
    else:
        dt = time.perf_counter() - _gc_start.get('t', time.perf_counter())
        if dt > 2:
            print(f'\nGC-STALL generation {info.get("generation")}: {dt:.1f} s', file=sys.__stderr__, flush=True)
            if dt > 20:
                import collections
                objs = gc.get_objects()
                top = collections.Counter(type(o).__name__ for o in objs).most_common(12)
                print(f'GC-STALL objects: {len(objs)}, top types: {top}', file=sys.__stderr__, flush=True)


gc.callbacks.append(_gc_timing)


@pytest.fixture(scope='module', autouse=True)
def freeze_survivors_of_each_module():
    """ Leave the objects still alive after a test module out of the later garbage collections

    The Qt widgets that tests leave behind (the Python wrappers of the widgets of closed windows, tens of
    thousands over the whole session) are not freed. The full collections would go through all of them again and
    again, which took minutes on the CI runners (PySide6), where it ended up failing the tests with a time limit.
    """
    yield
    gc.collect()
    gc.freeze()


#
# def _cleanup_qt_core():
#     """
#     Dynamically detects the active Qt backend in the current matrix run
#     and aggressively flushes/destroys remaining C++ environments.
#     """
#     # Supported Qt backends across the testing matrix
#     backends = ['PySide6', 'PyQt6', 'PyQt5']
#
#     for backend in backends:
#         try:
#             # Dynamically import the core module of the active backend
#             mod = __import__(f"{backend}.QtCore", fromlist=["QCoreApplication"])
#             app = mod.QCoreApplication.instance()
#
#             if app is not None:
#                 # Flush any pending events or delayed signals in the main event loop
#                 app.processEvents()
#
#
#                 # Attempt to safely close and destroy lingering UI widgets (ParameterTrees, Windows, etc.)
#                 try:
#                     widgets_mod = __import__(f"{backend}.QtWidgets", fromlist=["QApplication"])
#                     for widget in widgets_mod.QApplication.topLevelWidgets():
#                         if hasattr(widget, 'close'):
#                             try:
#                                 widget.close()
#                             except Exception:
#                                 pass
#                         if hasattr(widget, 'deleteLater'):
#                             widget.deleteLater()  # Schedule full C++ memory deletion
#
#                     # Process the deleteLater events immediately while the loop is still alive
#                     app.processEvents()
#                 except Exception:
#                     pass
#
#                 # Signal the application loop to quit and remove the reference
#                 app.quit()
#                 del app
#                 break  # Stop checking once the active backend is processed
#         except ImportError:
#             continue
#
#
# @pytest.fixture(autouse=True)
# def per_test_cleaner():
#     """
#     Runs automatically after EVERY single test case.
#     Prevents the 'snowball effect' where lingering references trigger random crashes mid-suite.
#     """
#     yield
#     # Force immediate garbage collection of temporary domain models and parameters
#     gc.collect()
#     try:
#         _cleanup_qt_core()
#     except Exception:
#         pass
#
#
# def pytest_sessionfinish(session, exitstatus):
#     """
#     Pytest lifecycle hook executed right BEFORE the coverage report is processed.
#     Breaks global registries that pytest-cov would otherwise trap in memory.
#     """
#     try:
#         from pyqtgraph.parametertree import Parameter
#         # Clear pyqtgraph's global dictionary cache containing your custom registered parameters
#         Parameter.PARAM_TYPES = {}
#     except Exception:
#         pass
#
#     # Flush memory before coverage locks the thread context
#     gc.collect()
#     _cleanup_qt_core()
#
#
# def pytest_unconfigure(config):
#     """
#     Final ultimate safety net executed right before the Python interpreter exits.
#     Ensures PySide/PyQt and Python close down in an orderly chronological sequence.
#     """
#     _cleanup_qt_core()
#     gc.collect()
