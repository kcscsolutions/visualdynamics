"""One playing at a time, in both views.

Where the averaging view meets a multi-capture record it shows a
single playing — channels overlaid on the flat plot, receding on the
stage — and the pager steps playings (Brandon, 2026-08-28, after
driving two concatenated layouts and loving neither). The marks sit
once, on the record's own clock; the panel's '20 × 3 = 60' row is
what tells the pooling.
"""

from __future__ import annotations

import numpy as np

from visualdynamics.core.data import TimeHistory
from visualdynamics.units import DEFAULT_SYSTEM

RATE = 1024.0
SAMPLES = 512


def _multi(captures=4, channels=('101Z+', '104Z+')):
    """A history the way imports build them: capture-major, one record
    per channel per capture."""
    t = np.arange(SAMPLES) / RATE
    rng = np.random.default_rng(8)
    rows, dofs = [], []
    for _capture in range(captures):
        for dof in channels:
            rows.append(rng.standard_normal(SAMPLES))
            dofs.append(dof)
    return TimeHistory(t, np.asarray(rows), response_dof=dofs,
                       ordinate_dim='acceleration')


def test_capture_indices_count_each_channels_playings():
    history = _multi(captures=3)
    assert history.capture_indices() == [0, 0, 1, 1, 2, 2], \
        'per channel, in pooling order — never a global record count'


def _showing(window, pump, history, flat=True):
    window.add_object('Run', history)
    item = window._item_for_object('Run')
    window.tree.clearSelection()
    item.setSelected(True)
    window.tree.setCurrentItem(item)
    pane = window.data_pane
    if pane.waterfall_action.isChecked() == flat:
        pane.waterfall_action.trigger()
    pane.averaging_action.setChecked(True)
    pane._choose_averaging(True)
    window.render_current()
    pump()
    return pane


def test_the_flat_averaging_view_shows_one_playing(window, pump):
    import pyqtgraph as pg

    history = _multi(captures=4)
    pane = _showing(window, pump, history)
    plots = [item for item in pane.graphics.ci.items
             if isinstance(item, pg.PlotItem)]
    curves = [c for c in plots[0].listDataItems()
              if c.xData is not None and len(c.xData)
              and not getattr(c, 'is_zone_edge', False)]
    assert len(curves) == 2, 'the two channels of one playing, no more'
    shown = history.display_ordinate(DEFAULT_SYSTEM, [0])[0]
    assert np.allclose(curves[0].yData, shown), \
        'page one is the first playing, in display units'
    assert max(np.nanmax(c.xData) for c in curves) <= SAMPLES / RATE, \
        'on the record\'s own clock'
    assert 'capture 1 of 4' in window._status_text
    assert len(window.averaging_overlays) == 1, 'the marks sit once'


def test_the_pager_steps_playings(window, pump):
    import pyqtgraph as pg

    history = _multi(captures=4)
    pane = _showing(window, pump, history)
    pane.page_box.setValue(3)
    pump()
    window.render_current()
    pump()
    assert 'capture 3 of 4' in window._status_text
    plots = [item for item in pane.graphics.ci.items
             if isinstance(item, pg.PlotItem)]
    curves = [c for c in plots[0].listDataItems()
              if c.xData is not None and len(c.xData)
              and not getattr(c, 'is_zone_edge', False)]
    shown = history.display_ordinate(DEFAULT_SYSTEM, [4])[0]
    assert np.allclose(curves[0].yData, shown), \
        'the third playing: records four and five'


def test_the_stage_shows_the_same_playing(window, pump):
    history = _multi(captures=4)
    _showing(window, pump, history, flat=False)
    assert 'capture 1 of 4' in window._status_text
    ordinals = history.capture_indices()
    assert {ordinals[i] for i in window._waterfall_drawn} == {0}, \
        'every staged record belongs to the playing on show'
    names = set(window.data_pane.waterfall_plotter.actors)
    assert 'marks-averaging-span' in names, \
        'the ordinary single marks, on the ordinary clock'


def test_a_single_capture_record_is_not_paged(window, pump):
    t = np.arange(SAMPLES) / RATE
    history = TimeHistory(
        t, np.random.default_rng(2).standard_normal((2, SAMPLES)),
        response_dof=['101Z+', '104Z+'], ordinate_dim='acceleration')
    _showing(window, pump, history)
    assert 'capture' not in window._status_text


def test_without_the_averaging_view_the_record_draws_whole(window, pump):
    """The one-playing reading belongs to the averaging view; the
    plain record view keeps showing everything, paged at fifty as it
    always was."""
    import pyqtgraph as pg

    history = _multi(captures=4)
    pane = _showing(window, pump, history)
    pane.averaging_action.setChecked(False)
    pane._choose_averaging(False)
    window.render_current()
    pump()
    plots = [item for item in pane.graphics.ci.items
             if isinstance(item, pg.PlotItem)]
    curves = [c for c in plots[0].listDataItems()
              if c.xData is not None and len(c.xData)
              and not getattr(c, 'is_zone_edge', False)]
    assert len(curves) == 8, 'all four playings of both channels'
    assert 'capture' not in window._status_text
