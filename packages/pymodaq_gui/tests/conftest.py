import os

import pytest

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """Run the deferred deletions once the fixtures are torn down

    pytest-qt and the fixtures close their widgets with ``deleteLater``, but processEvents does not run deferred
    deletions: without this, the closed windows pile up from test to test and every garbage collection gets slower
    (minutes on PySide6 CI).
    """
    from qtpy import QtCore
    if QtCore.QCoreApplication.instance() is not None:
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
