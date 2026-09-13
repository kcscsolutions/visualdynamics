"""One comparison at a time, and a way to reach the others.

A specification with the response it bounds is the thing being read.
Six of them on one axis is a thicket with no comparison visible in it,
so the plot draws one and the bar offers the rest.
"""

from __future__ import annotations

import pytest
from conftest import fixture_path

pytestmark = pytest.mark.usefixtures('flat_reading')

def loaded(window, pump):
    """A specification and a measurement covering several channels."""
    window.import_paths([fixture_path('plate', 'random_spectra.nc4')])
    pump()
    window.tree.clearSelection()
    from PySide6.QtCore import QItemSelectionModel

    for name in ('PSD', 'Specification'):
        item = window._item_for_object(name)
        item.setSelected(True)
        window.tree.setCurrentItem(
            item, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
    window.render_current()
    pump()


def curves(window):
    plots = [item for item in window.data_pane.graphics.ci.items
             if hasattr(item, 'listDataItems')]
    from visualdynamics.plot import data_curves

    return [c for plot in plots for c in data_curves(plot)]


def box(window):
    return window.data_pane.pair_box


def test_only_one_comparison_is_drawn(window, pump):
    loaded(window, pump)
    assert len(curves(window)) == 2, 'a specification and its response'


def test_the_bar_offers_the_others(window, pump):
    loaded(window, pump)
    assert window.data_pane.pair_action.isVisible()
    assert not window.data_pane.toolbar.isHidden(), (
        'an action can be visible inside a hidden bar, which is exactly '
        'how the drop-down went missing')
    assert box(window).count() > 1


def test_every_offered_pair_has_both(window, pump):
    """A channel with a specification and no measurement is not a
    comparison, and neither is the other way round."""
    from visualdynamics.plot import specification_pairs

    loaded(window, pump)
    _kinds, series = window._current_series()
    from visualdynamics.plot import bounded_by_specification

    series, _hidden = bounded_by_specification(series)
    offered = [box(window).itemData(i) for i in range(box(window).count())]
    assert offered == specification_pairs(series)


def test_picking_another_draws_that_one(window, pump):
    loaded(window, pump)
    first = {c.opts.get('name') for c in curves(window)}
    box(window).setCurrentIndex(1)
    pump()
    second = {c.opts.get('name') for c in curves(window)}
    assert len(curves(window)) == 2
    assert second != first


def test_the_choice_survives_a_redraw(window, pump):
    """The list is rebuilt every drawing. Held by position it would jump
    to another channel whenever one arrived or left."""
    loaded(window, pump)
    box(window).setCurrentIndex(2)
    pump()
    wanted = window.data_pane.chosen_pair()
    window.render_current()
    pump()
    assert window.data_pane.chosen_pair() == wanted


def test_a_single_comparison_needs_no_selector(window, pump):
    """Nothing to choose between."""
    loaded(window, pump)
    for name in ('PSD', 'Specification'):
        obj = window.objects[name]
        row = next(i for i in range(obj.num_records)
                   if obj.response_dof[i] == '101Z+'
                   and (obj.reference_dof is None
                        or obj.reference_dof[i] == '101Z+'))
        window._select_records(name, [row])
    window.render_current()
    pump()
    assert not window.data_pane.pair_action.isVisible()
    assert len(curves(window)) == 2


def test_a_psd_with_no_specification_is_not_cut_down(window, pump):
    """The restriction is about comparisons. A measurement on its own is
    all of itself. Counted on the flat plot: the waterfall is the
    default reading now, so it is asked for first."""
    window.data_pane.waterfall_action.setChecked(False)
    window.import_paths([fixture_path('plate', 'random_spectra.nc4')])
    pump()
    window.tree.clearSelection()
    window._item_for_object('PSD').setSelected(True)
    window.render_current()
    pump()
    assert len(curves(window)) > 2
    assert not window.data_pane.pair_action.isVisible()


def test_the_arrows_step_through_the_comparisons(window, pump):
    """The whole point of one at a time: getting to the next one has to
    be quick."""
    loaded(window, pump)
    first = window.data_pane.chosen_pair()
    window.data_pane.step_pair(1)
    pump()
    second = window.data_pane.chosen_pair()
    assert second != first
    window.data_pane.step_pair(-1)
    pump()
    assert window.data_pane.chosen_pair() == first


def test_stepping_redraws(window, pump):
    loaded(window, pump)
    before = {c.opts.get('name') for c in curves(window)}
    window.data_pane.step_pair(1)
    pump()
    assert {c.opts.get('name') for c in curves(window)} != before


def test_the_ends_do_not_wrap(window, pump):
    """Running off the bottom of a channel list and arriving back at the
    top reads as nothing having happened."""
    loaded(window, pump)
    for _ in range(box(window).count() + 5):
        window.data_pane.step_pair(1)
    assert box(window).currentIndex() == box(window).count() - 1
    for _ in range(box(window).count() + 5):
        window.data_pane.step_pair(-1)
    assert box(window).currentIndex() == 0


def test_stepping_does_nothing_without_a_choice(window, pump):
    """One comparison, or none: there is nowhere to step to, and the
    keys belong to whatever else wants them."""
    window.import_paths([fixture_path('plate', 'random_spectra.nc4')])
    pump()
    window.tree.clearSelection()
    window._item_for_object('PSD').setSelected(True)
    window.render_current()
    pump()
    assert not window.data_pane.pair_action.isVisible()
    window.data_pane.step_pair(1)      # must not raise
    pump()


def test_the_arrows_belong_to_the_plot_not_the_window(window, pump):
    """The tree moves its selection with the same keys. A window-wide
    shortcut would take them from it, so these are the pane's and reach
    only as far as its own children."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QShortcut

    loaded(window, pump)
    arrows = [s for s in window.data_pane.findChildren(QShortcut)
              if s.key().toString() in ('Up', 'Down')]
    assert len(arrows) == 2
    assert all(s.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
               for s in arrows)


def test_there_is_a_way_that_works_anywhere(window, pump):
    """Because the tree usually has the keyboard just after a
    selection, which is exactly when the next channel is wanted."""
    from PySide6.QtGui import QShortcut

    loaded(window, pump)
    keys = {s.key().toString() for s in window.findChildren(QShortcut)}
    assert 'Alt+Up' in keys and 'Alt+Down' in keys
