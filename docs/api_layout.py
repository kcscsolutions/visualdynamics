"""How the API reference is laid out: what is in it, and in what order.

Separate from `gen_api.py`, which writes the pages, because this half has
to be importable *without* the documentation tools installed —
`tests/test_docs.py` holds it to the package, and the test environment
has no mkdocs in it. Importing the writer runs it (that is how
mkdocs-gen-files scripts work), and running it needs mkdocs; importing
this runs nothing.
"""

from __future__ import annotations

import pkgutil

import visualdynamics

#: The reference is grouped by *package*, because that is what the
#: sidebar can collapse and what a reader already knows the shape of.
#: Every entry under a group shows its leaf name — `averaging`,
#: `channel_table` — since repeating `visualdynamics.core.` down a
#: column of thirty is thirty characters of prefix and no information.
#:
#: The order and the blurbs are the editorial part: the objects first,
#: then what is done to them, then what shows them, with the GUI last
#: because a script never touches it.
SECTIONS: list[tuple[str, str, str]] = [
    ('visualdynamics.core', 'The objects',
     ('Geometry, the data arrays, shapes and the analyses over them — '
      'the whole toolset without a window. The guide\'s '
      '[The objects](../guide/objects.md) is the map: every kind, what '
      'it stores, and what can be done with it; the pages below hold '
      'the signatures.')),
    ('visualdynamics.io', 'Reading and writing',
     ('Nearly everything the package reads it also writes — one module per '
      'format, and a round trip that is tested rather than assumed.')),
    ('visualdynamics.plot', 'Plotting',
     ('One renderer for the app and for scripting, so a plot drawn from '
      'a script is the plot the window draws.')),
    ('visualdynamics.viz', 'The 3D view',
     'Geometry, deflection and picking, over shared VTK buffers.'),
    ('visualdynamics.report', 'Reports',
     'Blocks bound to project objects, rendered to one self-contained page.'),
    ('visualdynamics.demo', 'The demonstration model',
     'The quadcopter and the plate the fixtures, the examples and the website are built from.'),
    ('visualdynamics.gui', 'The desktop app',
     ('The window and its panes. Nothing here is needed to use the '
      'toolset from a script, and no Qt is imported outside it.')),
    ('visualdynamics', 'The package',
     'What `import visualdynamics` puts in front of you.'),
]


def section_of(module: str) -> int:
    for index, (prefix, _title, _blurb) in enumerate(SECTIONS):
        if module == prefix or module.startswith(prefix + '.'):
            return index
    return len(SECTIONS) - 1


def package_of(module: str) -> str:
    """The package a module is listed under — its parent, or itself.

    `visualdynamics.core.geometry` is listed under `visualdynamics.core`;
    `visualdynamics` and its own modules are listed under
    `visualdynamics`.
    """
    parent = module.rpartition('.')[0]
    return parent or module


def leaf_of(module: str) -> str:
    """What the sidebar shows: the last segment, or the package name for
    the package's own page."""
    return module.rpartition('.')[2] if '.' in module else module


def grouped() -> list[tuple[str, str, list[str]]]:
    """[(package, blurb, [modules])], in the reading order above.

    Packages are ordered by the section they fall in, and within a
    section by name, so `visualdynamics.core` comes before
    `visualdynamics.io` and both come before the GUI.
    """
    packages: dict[str, list[str]] = {}
    for module in modules():
        packages.setdefault(package_of(module), []).append(module)
    blurbs = {prefix: blurb for prefix, _title, blurb in SECTIONS}
    return [(package, blurbs.get(package, ''), sorted(found))
            for package, found in sorted(
                packages.items(), key=lambda kv: (section_of(kv[0]), kv[0]))]


def modules() -> list[str]:
    """Every importable module in the package, dotted, sorted."""
    found = ['visualdynamics']
    for module in pkgutil.walk_packages(visualdynamics.__path__,
                                        'visualdynamics.'):
        leaf = module.name.rsplit('.', 1)[-1]
        if leaf.startswith('_'):
            continue          # __main__ and friends: not an API
        found.append(module.name)
    return sorted(found)


