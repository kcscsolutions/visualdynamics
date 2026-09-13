"""One drawing, one render.

pyvista's ``add_mesh`` renders by default, so a stage built from many
actors puts every intermediate frame on screen — a specification with
sixteen channels drew itself in 160 renders and the bands visibly
arrived one at a time (Brandon, 2026-09-01, random.vdyn). ``marks.py``
had defended one drawer by hand with ``render=False``; this is the
same rule for every stage drawer, in one place: rendering is
suppressed while a drawer runs, and the caller renders once after —
the GUI already does, and a screenshot renders for itself.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any


def one_render(draw: Callable[..., Any]) -> Callable[..., Any]:
    """Suppress renders for the drawer's whole run; the plotter is its
    first argument. Nested drawers restore the state they found."""
    @functools.wraps(draw)
    def quietly(plotter: Any, *args: Any, **kwargs: Any) -> Any:
        before = getattr(plotter, 'suppress_rendering', None)
        if before is None:                 # not a pyvista plotter
            return draw(plotter, *args, **kwargs)
        plotter.suppress_rendering = True
        try:
            return draw(plotter, *args, **kwargs)
        finally:
            plotter.suppress_rendering = before
    return quietly
