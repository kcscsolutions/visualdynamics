"""How wide the project dock is, is the user's.

It used to refit to its content on every import, expand, collapse and
rename. That reads well in a demo and badly in use: going back and forth
between a geometry and a photo set moved the dock under the cursor,
because the two names are different lengths. Now it is sized once, when
the window first appears, and never again.
"""

from __future__ import annotations

from conftest import fixture_path


def settle(window, pump):
    pump()          # the fit is deferred a turn so layout has happened
    pump()


def test_expanding_a_grid_leaves_the_width_alone(window, pump):
    """The one that used to widen it. A grid too wide for the dock is
    scrolled to, not resized around."""
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    settle(window, pump)
    before = window.project_dock.width()
    window._item_for_object('Time History').setExpanded(True)
    settle(window, pump)
    assert window.project_dock.width() == before


def test_moving_between_objects_leaves_the_width_alone(window, pump):
    """What was actually annoying: two objects with different name
    lengths, and the dock stepping in and out as the selection moved."""
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    settle(window, pump)
    widths = set()
    for name in list(window.objects)[:2] * 2:
        window.tree.clearSelection()
        item = window._item_for_object(name)
        item.setSelected(True)
        window.tree.setCurrentItem(item)
        window.render_current()
        settle(window, pump)
        widths.add(window.project_dock.width())
    assert len(widths) == 1, f'the dock moved: {sorted(widths)}'


def test_the_dock_never_takes_more_than_half_the_window(window, pump):
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    window._item_for_object('Time History').setExpanded(True)
    settle(window, pump)
    assert window.project_dock.width() <= window.width() // 2


def test_a_floating_dock_is_never_resized(window, pump, monkeypatch):
    """A floating panel's size belongs to the user; resizeDocks has nothing
    legitimate to act on and disturbed the main window's layout on macOS."""
    calls = []
    monkeypatch.setattr(window, 'resizeDocks',
                        lambda *args, **kwargs: calls.append(args))
    window.project_dock.setFloating(True)
    pump()
    calls.clear()
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    window._item_for_object('Time History').setExpanded(True)
    settle(window, pump)
    assert calls == [], 'fit ran against a floating dock'


def test_nothing_resizes_the_dock_after_the_first_show(window, pump,
                                                       monkeypatch):
    """Beyond the opening width, only the user's drag moves it."""
    settle(window, pump)
    calls = []
    monkeypatch.setattr(window, 'resizeDocks',
                        lambda *args, **kwargs: calls.append(args))
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    item = window._item_for_object('Time History')
    item.setExpanded(True)
    settle(window, pump)
    item.setExpanded(False)
    window.project_dock.setFloating(True)
    settle(window, pump)
    window.project_dock.setFloating(False)
    settle(window, pump)
    assert calls == [], f'something resized the dock: {calls}'


def test_it_opens_at_about_a_fifth_of_the_window(window, pump):
    """Fitted to an empty tree it opened as a strip too narrow to read a
    name in."""
    settle(window, pump)
    share = window.project_dock.width() / window.width()
    assert 0.15 <= share <= 0.30, share


def test_the_content_can_still_ask_for_more(window, pump):
    """A fifth is a floor, not a cap — a long name still gets its room,
    up to half the window."""
    window.import_paths([fixture_path('plate', 'modal_spectra.nc4')])
    settle(window, pump)
    assert window.project_dock.width() >= window.width() // 5
    assert window.project_dock.width() <= window.width() // 2


def test_the_tree_stays_in_the_window(window):
    """It is how you say what the views are of, and there is only ever
    the one window."""
    from PySide6.QtWidgets import QDockWidget

    features = window.project_dock.features()
    assert features & QDockWidget.DockWidgetFeature.DockWidgetMovable
    assert not features & QDockWidget.DockWidgetFeature.DockWidgetFloatable
    assert not features & QDockWidget.DockWidgetFeature.DockWidgetClosable
