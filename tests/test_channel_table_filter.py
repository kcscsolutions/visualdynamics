"""Picking channels in the tree's grid filters the table beside it.

The grid's cell selection is the record selection everywhere else — the
plot draws just the picked records — so the channel table does the same:
picked cells are the rows shown, and the whole table means the whole
object was selected.
"""

from __future__ import annotations

import pytest
from conftest import fixture_path

from visualdynamics import io


@pytest.fixture
def shown(window, pump):
    """The channel table added, expanded, and its grid at hand."""
    table = io.load(fixture_path('plate', 'channel_table.vdyn'))
    window.add_object('Channel Table', table)
    item = window.test_item.child(0)
    item.setExpanded(True)
    window.tree.setCurrentItem(item)
    pump()
    return window, table, window.record_grids['Channel Table']


def test_the_whole_object_shows_the_whole_table(shown):
    window, table, _grid = shown
    assert window.table.model().rowCount() == table.num_channels


def test_picked_cells_are_the_rows_shown(shown, pump):
    window, table, grid = shown
    grid.select_records([2, 5])
    window.render_current()
    pump()
    model = window.table.model()
    assert model.rowCount() == 2
    shown_channels = [model.data(model.index(r, 0)) for r in range(2)]
    assert shown_channels == [str(table['channel'][2]),
                              str(table['channel'][5])]
    assert '2 of' in window.statusBar().currentMessage()


def test_edits_in_the_filtered_view_land_on_the_right_channel(shown, pump):
    from PySide6.QtCore import Qt

    window, table, grid = shown
    grid.select_records([3])
    window.render_current()
    pump()
    model = window.table.model()
    assert model.setData(model.index(0, 1), '999', Qt.ItemDataRole.EditRole)
    assert table['node'][3] == '999', 'row 0 of the view is channel 3'


def test_deleting_a_filtered_row_deletes_the_right_channel(shown, pump):
    window, table, grid = shown
    doomed = int(table['channel'][4])
    survivor = int(table['channel'][0])
    grid.select_records([4])
    window.render_current()
    pump()
    window.table.selectRow(0)
    window.table.rows_deleted.emit([0])
    pump()
    channels = [int(c) for c in table['channel']]
    assert doomed not in channels, 'view row 0 was channel 4'
    assert survivor in channels
