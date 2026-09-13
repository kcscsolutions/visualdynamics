"""Renaming, and the row that was left out of it.

Every object in the tree renames by editing its row. The project's own
row looked like it did too — it is editable, it accepts the text, the
tree shows the new name — and underneath, nothing happened: the verb
started no edit, and an edit made by hand never reached `project.name`.

Nothing on screen showed the gap. It surfaced only where the project's
name is actually used: what a save writes, and what a drag out of the
window calls the file.
"""

from __future__ import annotations


def test_the_project_row_can_be_renamed(window, pump):
    """Rename did nothing at all on the one row that carries the
    project's name.

    `top_level_item` walks *up* to the project and answers None when the
    selection is already there — correct for finding an object's row,
    and the reason the verb was a silent no-op here.
    """
    window.tree.setCurrentItem(window.test_item)
    window.test_item.setSelected(True)
    pump()
    window.rename_selected()
    pump()
    assert window.tree.state() == window.tree.State.EditingState, (
        'Rename started no edit on the project row')


def test_renaming_the_project_row_renames_the_project(window, pump):
    """The row said one thing and `project.name` went on saying another.

    Nothing on screen showed it: the tree read correctly, and the old
    name came back out at the two moments that use it — saving, and
    dragging the project out of the window.
    """
    window.test_item.setText(0, 'Airplane Modal')
    pump()
    assert window.project.name == 'Airplane Modal'


def test_the_renamed_project_is_what_gets_saved(window, pump, tmp_path):
    """The consequence, from the outside."""
    window.test_item.setText(0, 'Airplane Modal')
    pump()
    written = window._write_for_drag(None, str(tmp_path))
    # basename by the OS's own rule — splitting on '/' read the whole
    # backslashed path as one name on Windows
    import os

    assert [os.path.basename(p) for p in written] == ['Airplane Modal.vdyn']

    import visualdynamics
    path = str(tmp_path / 'saved.vdyn')
    window.project.save(path)
    assert visualdynamics.Project.open(path).name == 'Airplane Modal'


def test_an_emptied_project_name_goes_back_rather_than_blank(window, pump):
    """A nameless project is not a state anything else can show."""
    window.test_item.setText(0, 'Airplane Modal')
    pump()
    window.test_item.setText(0, '   ')
    pump()
    assert window.test_item.text(0) == 'Airplane Modal'


def photos_window(window, pump, tmp_path):
    """A Photos object with two named photos, and its grid."""
    from PySide6.QtGui import QImage

    from visualdynamics.core.photos import Photos

    paths = []
    for name in ('Setup', 'Fixture'):
        path = tmp_path / f'{name}.png'
        QImage(8, 8, QImage.Format.Format_RGB32).save(str(path))
        paths.append(str(path))
    window.import_paths(paths)
    pump()
    name = next(n for n, o in window.objects.items() if isinstance(o, Photos))
    item = window._item_for_object(name)
    window.tree.setCurrentItem(item)
    item.setSelected(True)
    pump()
    return name, window.record_grids[name]


def test_rename_follows_the_photo_picked_in_the_grid(window, pump, tmp_path,
                                                     monkeypatch):
    """With one photo picked, Rename renames *that photo*.

    It used to rename the object holding it — not a refusal, which would
    at least say something, but the wrong rename carried out in silence.
    """
    name, grid = photos_window(window, pump, tmp_path)
    grid.select_records([1])
    pump()

    from PySide6.QtWidgets import QInputDialog
    monkeypatch.setattr(QInputDialog, 'getText',
                        staticmethod(lambda *a, **k: ('Fixture, from above',
                                                      True)))
    window.rename_selected()
    pump()
    assert list(window.objects[name].names) == ['Setup', 'Fixture, from above']
    assert name in window.objects, 'and the object itself kept its name'


def test_rename_with_no_photo_picked_still_renames_the_object(window, pump,
                                                              tmp_path):
    """An empty grid selection means the whole object, which is the
    tree's own rule everywhere else."""
    _name, grid = photos_window(window, pump, tmp_path)
    grid.clearSelection()
    pump()
    window.rename_selected()
    pump()
    assert window.tree.state() == window.tree.State.EditingState, (
        'the object row should be being edited')
