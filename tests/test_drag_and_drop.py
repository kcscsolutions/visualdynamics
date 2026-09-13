"""Dropping files anywhere on the window imports them.

It used to be the tree's job alone, which made a target of whatever the
tree happened to be — and on a fresh window it is sized to no content at
all, a strip about 90 px wide. Miss it and nothing happens, which reads
as the drop being ignored, so the file gets dragged over again.

The plot still refuses drops. pyqtgraph's GraphicsView ignores every drag
it is handed — its own source says the class "likes to consume drag
events" — while still advertising that it accepts them, so a drag routed
to it is recorded nowhere and warned about on the way out.
"""

from __future__ import annotations

from conftest import fixture_path
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent


def drag_across(app, widget, mime):
    """A drag that enters and leaves, delivered the way Qt delivers one."""
    messages = []
    qInstallMessageHandler(lambda mode, context, text: messages.append(str(text)))
    try:
        app.sendEvent(widget, QDragEnterEvent(
            QPoint(10, 10), Qt.DropAction.CopyAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        app.sendEvent(widget, QDragLeaveEvent())
        app.processEvents()
    finally:
        qInstallMessageHandler(None)
    return [text for text in messages if 'drag' in text.lower()]


def file_drag():
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(fixture_path('plate',
                                                  'geometry.npz'))])
    return mime


def test_the_plot_does_not_claim_to_take_drops(qt_app, window):
    """This is the whole fix. Qt routes drag events only to widgets that say
    they accept drops, so refusing here means the plot never sees one."""
    assert not window.data_pane.graphics.acceptDrops()
    assert not window.data_pane.graphics.viewport().acceptDrops()


def test_the_window_takes_a_drop_wherever_it_lands(qt_app, window):
    """The fix for having to drop a file three times."""
    from PySide6.QtGui import QDropEvent

    # sent, not called: `acceptDrops()` is true either way, because Qt
    # sets it up the parent chain when a child takes drops. What matters
    # is whether the window itself answers the event.
    mime = file_drag()
    enter = QDragEnterEvent(QPoint(400, 400), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
    qt_app.sendEvent(window, enter)
    assert enter.isAccepted(), 'a file dragged onto the window is welcome'

    qt_app.sendEvent(window, QDropEvent(
        QPoint(400, 400), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    for _ in range(6):
        qt_app.processEvents()
    assert 'Geometry' in window.objects, list(window.objects)


def test_a_drag_of_something_that_is_not_a_file_is_left_alone(qt_app, window):
    from PySide6.QtCore import QMimeData

    mime = QMimeData()
    mime.setText('not a file')
    enter = QDragEnterEvent(QPoint(400, 400), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
    qt_app.sendEvent(window, enter)
    assert not enter.isAccepted()


# ---- and on the tree, which is where it kept missing --------------------


def drop_on(app, widget, mime):
    """A drag delivered to one widget, the way Qt delivers one to the
    widget actually under the cursor.

    Sent to the widget rather than to the window on purpose. Every test
    above sends to the window, which is what let a broken route pass
    them: the window's handlers work perfectly well when something else
    has already decided the window is the target.

    What this cannot check is the routing itself. `sendEvent` delivers
    to whatever it is handed, `acceptDrops` and all — so these say the
    handler does the right thing once reached, and the two flag tests
    above are what say it is reached. Reversing the two lines in
    `ProjectTree.__init__` fails those and not these.
    """
    from PySide6.QtGui import QDropEvent

    at = QPoint(10, 10)
    app.sendEvent(widget, QDragEnterEvent(
        at, Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    event = QDropEvent(at, Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)
    app.sendEvent(widget, event)
    app.processEvents()          # the import is queued, not immediate
    return event


def test_the_tree_takes_drops_and_its_viewport_does_too(qt_app, window):
    """The viewport is the child actually under the cursor. Accepting on
    the view alone leaves the drag resolving to a widget that refuses,
    and then it depends on Qt walking up out of a dock — which is what
    made dropping on the tree miss."""
    assert window.tree.acceptDrops()
    assert window.tree.viewport().acceptDrops()


def test_the_mode_is_set_before_the_flags(qt_app, window):
    """setDragDropMode clears acceptDrops on the view and its viewport,
    so accepting first accepts nothing. This is that ordering, pinned."""
    from visualdynamics.gui.project_tree import ProjectTree

    fresh = ProjectTree()
    assert fresh.acceptDrops() and fresh.viewport().acceptDrops()


def test_a_file_dropped_on_the_tree_is_imported(qt_app, window):
    """The whole report: this is the route that kept missing."""
    was = len(window.objects)
    event = drop_on(qt_app, window.tree.viewport(), file_drag())
    assert event.isAccepted()
    assert len(window.objects) > was


def test_a_file_dropped_on_the_tree_itself_is_imported(qt_app, window):
    was = len(window.objects)
    drop_on(qt_app, window.tree, file_drag())
    assert len(window.objects) > was


def test_the_tree_leaves_a_drag_that_is_not_files_alone(qt_app, window):
    """Ignoring rather than accepting is what lets anything else carry
    on to whoever it was meant for."""
    from PySide6.QtGui import QDropEvent

    mime = QMimeData()
    mime.setText('not a file')
    event = QDropEvent(QPoint(10, 10), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)
    qt_app.sendEvent(window.tree, event)
    assert not event.isAccepted()


def test_the_tree_never_hands_a_drop_to_the_view_machinery(qt_app, window):
    """QAbstractItemView decides what a drop means from the item under
    the cursor and the drag-drop mode, which is how importing became a
    matter of which row you happened to be over. None of the three
    overrides calls up to it."""
    from visualdynamics.gui.project_tree import ProjectTree

    for name in ('dragEnterEvent', 'dragMoveEvent', 'dropEvent'):
        assert name in vars(ProjectTree), f'{name} is not overridden'
    assert window.tree.dragDropMode() is not \
        window.tree.DragDropMode.InternalMove


# ---- the tree does not import its own project -----------------------------

def test_the_project_dragged_back_onto_the_tree_does_nothing(qt_app, window):
    """A whole-project drag names no objects — the project row is not an
    object — so by the time it reaches a drop it is nothing but a
    `.vdyn`, indistinguishable from the same file dragged in from
    Finder. Imported, every object in the project arrived a second time.

    There is no reading under which bringing it back means anything, so
    the drop does nothing at all.
    """
    from visualdynamics.gui import project_tree

    was = dict(window.objects)
    mime = project_tree._DraggedObjects(
        [], write=lambda folder: window._write_for_drag(None, folder))
    assert mime.urls(), 'it still writes the file — Finder gets one'

    event = drop_on(qt_app, window.tree.viewport(), mime)
    assert not event.isAccepted(), 'and the gesture reads as "not here"'
    assert dict(window.objects) == was, 'nothing arrived twice'


def test_the_same_file_from_finder_still_imports(qt_app, window, tmp_path):
    """The marker is on the drag, not on the file. Saved to the desktop
    and dragged in tomorrow, that project is an ordinary import."""
    import os

    from PySide6.QtCore import QUrl

    written = window._write_for_drag(None, str(tmp_path))
    assert [os.path.basename(p) for p in written] == ['Project.vdyn']

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(written[0])])
    event = drop_on(qt_app, window.tree.viewport(), mime)
    assert event.isAccepted()


# ---- the dock's chrome takes a file drag too ------------------------------

def test_everything_over_the_project_dock_takes_a_file_drag(qt_app, window):
    """The dock's chrome — its title bar, the toolbar, the holder
    around the tree — accepted nothing, and a drag refused there was
    left to Qt walking up to the window, which through a dock's widget
    stack is the walk that misses. On a fresh window the tree is a
    strip about 90 px wide, so most of the left side *was* chrome:
    importing by drop worked on the right half of the window and only
    sometimes on the left, aimed at the one place that names the
    project.

    Every widget over the dock now sits under something that accepts
    drops, so no drop there depends on that walk.
    """
    from PySide6.QtCore import QPoint

    window.resize(1200, 800)
    window.show()
    qt_app.processEvents()

    dock = window.project_dock

    def covered(widget):
        # up to the dock and no further: the window itself accepts,
        # but reaching it is the unreliable walk this fix removes, so
        # counting it would make this test unable to fail
        while widget is not None:
            if widget.acceptDrops():
                return True
            if widget is dock:
                return False
            widget = widget.parentWidget()
        return False

    corner = dock.mapTo(window, QPoint(0, 0))
    uncovered = {
        type(child).__name__
        for x in range(corner.x(), corner.x() + dock.width(), 8)
        for y in range(corner.y(), corner.y() + dock.height(), 8)
        if (child := window.childAt(QPoint(x, y))) is not None
        and not covered(child)}
    assert uncovered == set(), uncovered


def test_a_file_dropped_on_the_dock_chrome_is_imported(qt_app, window):
    """Not merely accepted — the drop reaches the importer.

    The flag is asserted separately because `sendEvent` does not
    consult it: real platform drag routing offers the drag only to
    widgets whose `acceptDrops` is set, so a handler behind a cleared
    flag passes this drop and never sees a real one.
    """
    assert window.project_dock.acceptDrops()
    assert window.project_dock.widget().acceptDrops()
    was = len(window.objects)
    event = drop_on(qt_app, window.project_dock.widget(), file_drag())
    assert event.isAccepted()
    assert len(window.objects) > was


def test_the_projects_own_drag_is_still_refused_there(qt_app, window):
    """The dock funnels through `dropped_files`, which answers empty
    for a drag of our own — the whole-project drag must not import a
    copy of itself through the chrome either."""
    from visualdynamics.gui.project_tree import _DraggedObjects

    was = dict(window.objects)
    mime = _DraggedObjects(
        [], write=lambda folder: window._write_for_drag(None, folder))
    event = drop_on(qt_app, window.project_dock.widget(), mime)
    assert not event.isAccepted()
    assert dict(window.objects) == was


# ---- a drop answers immediately, however long the import takes ------------

def test_a_drop_is_acknowledged_before_the_import_runs(qt_app, window):
    """A project file runs to hundreds of megabytes and half a minute,
    and for all of it the window used to say nothing. A drop that
    answers with thirty silent seconds is indistinguishable from a drop
    that was ignored — so the file got dragged again, somewhere else,
    and the second spot got credit for the first one's work: reported
    as 'dropping on the tree doesn't always work, the right side does'.
    """
    from conftest import fixture_path
    from PySide6.QtWidgets import QApplication

    path = fixture_path('plate', 'geometry.unv')
    window._import_after_drop([path])
    # before a single event is processed: the status is up and the
    # cursor says busy, while the import itself is still queued
    assert 'Importing' in window.statusBar().currentMessage()
    assert 'geometry.unv' in window.statusBar().currentMessage()
    assert QApplication.overrideCursor() is not None, 'busy cursor is on'
    assert len(window.objects) == 0, 'the import has not run yet'

    qt_app.processEvents()
    assert len(window.objects) == 1
    assert QApplication.overrideCursor() is None, 'and off again'
    assert window.statusBar().currentMessage().startswith('Imported ')


def test_the_cursor_is_restored_even_when_the_import_fails(qt_app, window,
                                                           tmp_path):
    from PySide6.QtWidgets import QApplication, QMessageBox

    bad = tmp_path / 'broken.unv'
    bad.write_text('not a universal file')
    shown = []
    original = QMessageBox.warning
    QMessageBox.warning = staticmethod(
        lambda *a, **k: shown.append(a) or QMessageBox.StandardButton.Ok)
    try:
        window._import_after_drop([str(bad)])
        qt_app.processEvents()
    finally:
        QMessageBox.warning = original
    assert shown, 'the failure was reported'
    assert QApplication.overrideCursor() is None, (
        'a failed import must not leave the window stuck busy')
