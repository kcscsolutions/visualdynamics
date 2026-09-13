"""The Qt binding, which has to be settled before a window exists.

This file used to run `gui_smoke_script.py` as well — 1922 lines driving
the whole application in a subprocess, twenty seconds here and nearly
four minutes on a CI runner. A coverage diff against the rest of the
suite put its unique reach at 501 lines of visualdynamics; twelve focused
files took that to a handful of icon-drawing and unreachable-guard
lines, and it was retired. `git log` for the files that replaced it.
"""


def test_vibe_steers_pyqtgraph_onto_its_own_qt_binding(qt_app):
    """pyqtgraph prefers PyQt6 over PySide6 when nothing is imported yet, so
    merely having PySide6 installed does not settle it."""
    from visualdynamics.gui import check_qt_binding

    check_qt_binding()
    import pyqtgraph

    assert pyqtgraph.Qt.QT_LIB == 'PySide6'


def test_a_foreign_qt_binding_is_refused_with_a_readable_reason(qt_app,
                                                               monkeypatch):
    """When something else got to pyqtgraph first — sdynpy imports it with
    PyQt5 at `import sdynpy` — the binding cannot be undone, and the failure
    used to surface as `QSplitter.addWidget called with wrong argument
    types` from deep inside the main window, naming nothing useful."""
    import pytest

    from visualdynamics.gui import check_qt_binding

    check_qt_binding()
    import pyqtgraph

    monkeypatch.setattr(pyqtgraph.Qt, 'QT_LIB', 'PyQt5')
    with pytest.raises(RuntimeError) as raised:
        check_qt_binding()
    message = str(raised.value)
    assert 'PyQt5' in message and 'PySide6' in message
    assert 'sdynpy' in message, 'name the usual culprit'
    assert 'launch_gui' in message, (
        'and the way out: it starts the app in its own process')
