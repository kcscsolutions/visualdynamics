"""The report page follows the project (Brandon, 2026-09-03).

He deleted the mode shapes, re-fitted five modes, re-made the matched
modes, and opened the report: one vertical line where five marks
belonged, and the matched-mode figures gone. The page had rendered
when the first mode was confirmed — that added and linked a set —
and nothing rebuilt it afterwards: later confirms replace the set in
place, and the matched set joins no group, so neither reached the
few triggers that existed (links, renames, a settled drag). Every
object change reaches the page now, debounced; a page off screen is
marked stale and rebuilt when shown.
"""

from __future__ import annotations

import json

from conftest import fixture_path
from conftest import select_objects as _select
from PySide6.QtTest import QTest

import visualdynamics
from visualdynamics.gui.main_window import REPORT_SETTLE_MS


def _page(window):
    path = window.report_editor._page_path
    with open(path, encoding='utf-8') as handle:
        html = handle.read()
    start = html.index('"blocks":')
    i = html.index('[', start)
    depth, j = 0, i
    while True:
        depth += html[j] == '['
        depth -= html[j] == ']'
        j += 1
        if depth == 0:
            break
    return json.loads(html[i:j])


def _rows_of(window, caption):
    for block in _page(window):
        if (block.get('caption') or '').startswith(caption):
            return len(block.get('rows') or block.get('marks') or [])
    return None


def _modal_report(window, pump, survey):
    shapes, frfs = survey
    window.set_project_type('Modal Test')
    window.add_object('Geometry', visualdynamics.import_file(
        fixture_path('plate', 'geometry.npz')))
    window.add_object('FRF', frfs)
    pump()
    window.generate_typed_report()
    pump()
    report = next(n for n, o in window.objects.items()
                  if type(o).__name__ == 'Report')
    _select(window, pump, report)
    return shapes, report


def _settle(pump):
    QTest.qWait(REPORT_SETTLE_MS + 100)
    pump()


def test_an_added_set_reaches_the_report(window, pump, survey):
    """Adding moves the tree's selection to the new object, which
    takes the report off screen — so the page is marked stale, not
    rebuilt, and the rebuild comes with the next look at it."""
    shapes, report = _modal_report(window, pump, survey)
    assert _rows_of(window, 'Identified modal parameters') is None, (
        'no shape set yet: the block is unbound and skipped')
    window.add_object('Modes', shapes)
    _settle(pump)
    assert window.report_editor.stale
    _select(window, pump, report)
    assert _rows_of(window, 'Identified modal parameters') == shapes.num_shapes


def test_a_set_replaced_in_place_reaches_the_open_report(window, pump,
                                                         survey):
    """What the fit does on every Confirm after the first: the same
    object, one more mode, no new link."""
    from visualdynamics.core.shapes import ShapeSet

    shapes, report = _modal_report(window, pump, survey)
    first = ShapeSet(shapes.frequency[:1], shapes.damping[:1],
                     list(shapes.coordinate), shapes.shape_matrix[:1])
    window.add_object('Modes', first)
    _settle(pump)                 # the add's own debounce runs out first
    _select(window, pump, report)
    assert _rows_of(window, 'Identified modal parameters') == 1
    assert window.report_editor.isVisible()
    # the in-place replacement, exactly as _publish_fit writes it, with
    # the report on screen: the debounced rebuild, not the stale flag
    window.objects['Modes'] = shapes
    window._refresh_item(window._item_for_object('Modes'), shapes)
    window._report_content_changed(settling=True)
    _settle(pump)
    assert _rows_of(window, 'Identified modal parameters') == shapes.num_shapes


def test_a_report_off_screen_is_rebuilt_when_shown_again(window, pump,
                                                         survey):
    """Changes made while another object is selected must not cost a
    rebuild each — 254 ms per change on a real project — and must not
    be lost either: the page is marked stale and rebuilt on show."""
    shapes, report = _modal_report(window, pump, survey)
    _select(window, pump, 'FRF')
    assert not window.report_editor.isVisible()
    window.add_object('Modes', shapes)
    _settle(pump)
    assert window.report_editor.stale
    assert _rows_of(window, 'Identified modal parameters') is None, (
        'not rebuilt while hidden')
    _select(window, pump, report)
    assert not window.report_editor.stale
    assert _rows_of(window, 'Identified modal parameters') == shapes.num_shapes


def test_a_removed_set_leaves_the_open_report(window, pump, survey):
    shapes, report = _modal_report(window, pump, survey)
    window.add_object('Modes', shapes)
    _settle(pump)
    _select(window, pump, report)
    assert _rows_of(window, 'Identified modal parameters') == shapes.num_shapes
    assert window.report_editor.isVisible()
    window._remove_object('Modes')
    _settle(pump)
    assert _rows_of(window, 'Identified modal parameters') is None
