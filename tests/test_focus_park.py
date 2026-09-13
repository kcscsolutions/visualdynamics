"""Keyboard focus is parked while the window is inactive.

macOS 26 with Qt 6.11 discards a Finder drop released over the rect of
the widget that held focus when the app deactivated: enter and update
are answered Copy, and the release still arrives as draggingExited — no
drop, no error, nothing. The tree is the first focusable widget, so on
a fresh window the one dead spot was the very widget whose status line
says "drag files onto the tree".

The hunt that found this — swizzling the NSView's dragging-destination
methods and toggling one variable at a time — cannot run in CI, so
these tests pin the *mechanism*: the handoff to a zero-size widget at
deactivation, and the return on activation. Three cheaper shapes of the
fix failed on the real machine first (parking at drag-enter, clearing
focus to nobody, disabling input methods); the handoff is what
delivered, five runs against two controls.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent


def _deactivate(qt_app, window):
    qt_app.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))


def _activate(qt_app, window):
    qt_app.sendEvent(window, QEvent(QEvent.Type.WindowActivate))


def test_focus_is_handed_off_at_deactivation(qt_app, window):
    """Handed off, not cleared: focus-to-nobody leaves the platform's
    input state armed, and only a genuine handoff to another widget
    runs the full teardown. That distinction cost three real-machine
    rounds to learn."""
    window.show()
    window.tree.setFocus()
    qt_app.processEvents()
    assert window.focusWidget() is window.tree

    _deactivate(qt_app, window)
    assert window.focusWidget() is window._focus_park, (
        'focus went to the parking widget, not to nobody')


def test_the_parking_widget_has_no_rect_to_poison(window):
    """The bug poisons the focused widget's rect; this rect cannot be
    hit by a drop."""
    assert window._focus_park.size().isEmpty()


def test_focus_comes_back_on_activation(qt_app, window):
    window.show()
    window.tree.setFocus()
    qt_app.processEvents()
    _deactivate(qt_app, window)
    _activate(qt_app, window)
    assert window.focusWidget() is window.tree, 'as if nothing happened'


def test_a_focus_taken_while_away_is_respected(qt_app, window):
    """If something else claimed focus while the window was inactive —
    a dialog handing it somewhere on close — the return must not
    steal it back."""
    window.show()
    window.tree.setFocus()
    qt_app.processEvents()
    _deactivate(qt_app, window)
    window.unit_combo.setFocus()
    qt_app.processEvents()
    _activate(qt_app, window)
    assert window.focusWidget() is window.unit_combo


def test_an_unfocused_window_parks_nothing(qt_app, window):
    window.show()
    focused = window.focusWidget()
    if focused is not None:
        focused.clearFocus()
    qt_app.processEvents()
    _deactivate(qt_app, window)
    _activate(qt_app, window)
    assert window.focusWidget() is not window._focus_park


def test_our_own_popup_does_not_park(qt_app, window, pump):
    """A combo's drop-down list is its own window on macOS 26, and its
    opening deactivates the main window — parking then hands focus
    away from the editor, which closes the popup the instant it opens
    (Brandon, 2026-08-30: the units drop-down was unusable). The park
    exists for drags arriving from *another app*; while our popup is
    up, the app never lost the stage."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget

    window.show()
    window.tree.setFocus()
    qt_app.processEvents()
    popup = QWidget(None, Qt.WindowType.Popup)
    popup.show()
    pump()
    try:
        _deactivate(qt_app, window)
        assert window.focusWidget() is window.tree, (
            'our own popup took the stage; the focus stays where the '
            'editor needs it')
    finally:
        popup.close()
