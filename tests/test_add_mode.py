"""Creating geometry by clicking in the 3D view.

The one gesture in visualdynamics that *makes* something out of nothing: the
`+` on the toolbar arms it, and after that a click in the view is a
node, a coordinate system, or the next corner of an element. It is also
the part with the most state — what is being edited, what the cursor is
over, which nodes are half-picked — and it was covered only by the
legacy end-to-end script, twenty seconds in a subprocess whose failures
name a line number in a 1900-line file.

The clicks go in through `_add_at` and `hover_at`, which is how a click
arrives from VTK anyway; `conftest`'s offscreen plotter gives a real
projector, so the screen positions are the ones a mouse would land on.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import edit_category as edit
from conftest import fixture_path


@pytest.fixture
def plate(window, pump):
    """The beam plate as exodus — 45 nodes and 32 quads.

    The `.npz` of the same plate is tracelines only, and half of what is
    checked here is about elements that are already there.
    """
    window.import_paths([fixture_path('plate', 'geometry.exo')])
    pump()
    return window.objects['Geometry']


def screen_of(window):
    return window._projector.screen()[0]


def test_the_plus_appears_with_editing_and_says_what_it_will_do(plate, window,
                                                               pump):
    """Show only what applies: there is nothing to add until a category
    says what a new thing would be."""
    assert not window.add_action.isVisible(), 'nothing is being edited'
    edit(window, pump, 'Nodes')
    assert window.add_action.isVisible()
    assert not window.add_mode, 'shown, not armed'
    window.set_add_mode(True)
    assert 'click in the view to place a node' in \
        window.statusBar().currentMessage()
    edit(window, pump, 'Coordinate systems')
    window.set_add_mode(True)
    assert 'place a coordinate system' in window.statusBar().currentMessage()


def test_a_node_lands_where_the_click_did(plate, window, pump):
    """And on the model's own surface: the plate is flat, so a node
    placed on it has to arrive at z = 0 rather than somewhere along the
    ray the cursor cast."""
    edit(window, pump, 'Nodes')
    window.set_add_mode(True)
    screen = screen_of(window)
    before = plate.num_nodes
    window._add_at(*(screen[0] + screen[8]) / 2)
    assert plate.num_nodes == before + 1
    assert abs(float(plate.node_xyz[-1][2])) < 1e-9, 'on the plate, not above'
    assert 'Added node' in window.statusBar().currentMessage()
    assert window.table.model().rowCount() == plate.num_nodes, (
        'the table beside the model is the model'
    )


def test_a_coordinate_system_lands_where_the_click_did_too(plate, window,
                                                           pump):
    edit(window, pump, 'Coordinate systems')
    window.set_add_mode(True)
    screen = screen_of(window)
    before = len(plate.cs_id)
    window._add_at(*(screen[0] + screen[8]) / 2)
    assert len(plate.cs_id) == before + 1
    assert 'Added coordinate system' in window.statusBar().currentMessage()


def test_the_element_types_are_offered_only_while_adding_one(plate, window,
                                                             pump):
    """Nothing else is built from a node count, so the tri/quad/beam
    buttons belong to elements in add mode and nowhere else."""
    edit(window, pump, 'Nodes')
    window.set_add_mode(True)
    assert not any(a.isVisible() for a in window.element_type_actions.values())
    edit(window, pump, 'Elements')
    assert not any(a.isVisible() for a in window.element_type_actions.values()), (
        'editing elements is not yet adding one'
    )
    window.set_add_mode(True)
    assert all(a.isVisible() for a in window.element_type_actions.values())
    assert window.element_type_actions['tri'].isChecked(), 'the default'
    assert window.element_type == (41, 3)
    assert window._picking_component() == 'nodes', (
        'an element is built out of nodes, so that is what the cursor picks')


def test_each_element_type_commits_on_its_own_node_count(plate, window, pump):
    edit(window, pump, 'Elements')
    window.set_add_mode(True)
    screen = screen_of(window)

    def pick(rows):
        for n, row in enumerate(rows):
            window.hover_at(*screen[row])
            window._add_at(*screen[row], extend=n > 0)

    for kind, rows, code in (('tri', (0, 1, 6), 41),
                             ('quad', (0, 1, 6, 5), 44),
                             ('beam', (2, 3), 21)):
        window.element_type_actions[kind].trigger()
        assert not window._picked_nodes, (
            'switching type drops a part-built element')
        before = len(plate.elem_conn)
        pick(rows)
        assert len(plate.elem_conn) == before + 1, f'{kind} did not commit'
        assert int(plate.elem_type[-1]) == code
        assert not window._picked_nodes, 'the pick list resets after committing'


def test_a_traceline_is_as_long_as_you_say_and_commits_on_enter(plate, window,
                                                                pump):
    """A traceline has no node count to commit on — it is however many
    were picked — so it is the one that needs saying when it is done."""
    edit(window, pump, 'Tracelines')
    window.set_add_mode(True)
    screen = screen_of(window)
    before = len(plate.traceline_conn)
    for n, row in enumerate((2, 3, 4)):
        window.hover_at(*screen[row])
        window._add_at(*screen[row], extend=n > 0)
    assert len(plate.traceline_conn) == before, 'still being drawn'
    window.commit_action.trigger()
    pump()
    assert len(plate.traceline_conn) == before + 1
    assert len(plate.traceline_conn[-1]) == 3


def test_the_cursor_lights_the_node_it_is_over_not_an_element_of_that_id(
        plate, window, pump):
    """While building an element the picker returns nodes, and the hover
    mesh has to light one — ids are shared between the groups, so drawing
    'entity 6' without asking which group would light a face."""
    edit(window, pump, 'Elements')
    window.set_add_mode(True)
    screen = screen_of(window)
    window.hover_at(*screen[6])
    assert window._hovered == int(plate.node_id[6])
    assert list(window._hover_mesh.verts) == [1, 6]


def test_leaving_add_mode_and_editing_puts_the_toolbar_back(plate, window,
                                                            pump):
    edit(window, pump, 'Nodes')
    window.set_add_mode(True)
    window.escape_action.trigger()
    pump()
    assert window.editing is None, 'Escape leaves editing'
    assert not window.add_mode
    assert not window.add_action.isVisible(), '+ hides when not editing'


def test_the_pencil_on_the_tree_opens_the_table_and_closes_it(plate, window,
                                                              pump):
    """Editing lives on the tree's own pencil, not on a toolbar button —
    and the toolbar's state carrier follows it either way."""
    item = window._item_for_object('Geometry')
    item.setExpanded(True)
    pump()
    nodes = item.child(0)
    assert not nodes.icon(1).isNull(), 'every category wears the pencil'
    window._tree_item_clicked(nodes, 1)
    pump()
    assert window.editing == ('Geometry', 'nodes')
    assert window.edit_toggle_action.isChecked()
    window._tree_item_clicked(nodes, 1)
    pump()
    assert window.editing is None, 'the second click closes it'
    assert not window.edit_toggle_action.isChecked()
    assert not window.add_action.isVisible()


def test_an_edit_that_would_break_the_model_is_refused_at_entry(plate, window,
                                                               pump):
    """Never written and complained about afterwards."""
    edit(window, pump, 'Elements')
    model = window.table.model()
    column = [c.title for c in model.columns].index('Nodes')
    kept = list(plate.elem_conn[0])
    assert model.setData(model.index(0, column), '101 99999') is False
    assert list(plate.elem_conn[0]) == kept, 'refused, not written'
    assert 'unknown nodes' in window.statusBar().currentMessage()
    assert model.setData(model.index(0, column), '101 102 103 104') is True
    assert list(plate.elem_conn[0]) == [101, 102, 103, 104]


def test_the_geometry_is_still_valid_after_all_of_that(plate, window, pump):
    """The point of the end-to-end script was that a session of edits
    leaves something loadable, which is worth keeping as a claim."""
    edit(window, pump, 'Nodes')
    window.set_add_mode(True)
    screen = screen_of(window)
    window._add_at(*(screen[0] + screen[8]) / 2)
    edit(window, pump, 'Elements')
    window.set_add_mode(True)
    for n, row in enumerate((0, 1, 6)):
        window.hover_at(*screen[row])
        window._add_at(*screen[row], extend=n > 0)
    window.stop_editing()
    pump()
    plate.validate()
    assert np.isfinite(plate.node_xyz).all()
