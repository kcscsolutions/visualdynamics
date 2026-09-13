"""A dropped file is imported after the drop, not during it.

macOS delivers a drop from inside its own drag run loop — the crash report
showed `NSCoreDragReceiveMessageProc` spinning one and pumping it, with a
pyqtgraph curve item painting from inside. Anything done in the drop handler
therefore runs with a nested loop live and free to deliver paint events, so
importing a file and rebuilding the plot there means Qt can paint a scene
halfway through being replaced.

The fix is not to make painting safe; it is to not be mutating the scene at
that moment.
"""

from __future__ import annotations

from conftest import fixture_path
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent


def drop(window, *paths):
    """Deliver a file drop the way Qt delivers one."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
    window.dragEnterEvent(QDragEnterEvent(
        QPoint(10, 10), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    window.dropEvent(QDropEvent(
        QPoint(10, 10), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))


def test_nothing_is_imported_while_the_drop_is_still_running(window):
    """The whole point: when dropEvent returns, the scene is untouched."""
    drop(window, fixture_path('plate', 'geometry.npz'))
    assert window.objects == {}, 'imported inside the drop'
    assert window.test_item.childCount() == 0


def test_it_is_imported_once_the_event_loop_turns(window, pump):
    drop(window, fixture_path('plate', 'geometry.npz'))
    pump()
    assert list(window.objects) == ['Geometry']


def test_several_files_all_arrive(window, pump):
    drop(window,
         fixture_path('plate', 'geometry.npz'),
         fixture_path('plate', 'modal_spectra.nc4'))
    pump()
    assert 'Geometry' in window.objects
    assert 'Modal FRF' not in window.objects, 'named for its type'
    assert 'FRF' in window.objects


def test_a_drop_onto_a_window_already_showing_a_plot(window, pump):
    """The crashing case: a scene exists and is being replaced.

    Nothing here can prove a SIGBUS is gone — it was never reproducible on
    demand — but the mutation now happens with no nested loop live, which is
    the only reentrancy the crash stack showed.
    """
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    window.tree.setCurrentItem(window._item_for_object('FRF'))
    pump()
    assert window.data_pane.isVisible()
    before = len(window.objects)
    drop(window, fixture_path('plate', 'random_spectra.nc4'))
    assert len(window.objects) == before, 'still untouched inside the drop'
    pump()
    assert len(window.objects) > before
