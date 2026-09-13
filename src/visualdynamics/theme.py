"""Light/dark theme colors shared by the 3D view, 2D plots, and the GUI.

Qt's native style already follows the OS appearance for widgets; the things
visualdynamics draws itself (the VTK scene and pyqtgraph plots) have to be told, which
is what these colors are for.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LIGHT = {
    'name': 'light',
    'scene_background': '#ffffff',
    # flat, equal to the base: the gradient read as depth for a while
    # and then read as clutter (Brandon, 2026-08-23) — pure white and
    # pure black let the data carry the scene
    'scene_background_top': '#ffffff',
    'scene_text': '#1c1c1e',
    'plot_background': '#ffffff',
    'plot_background_top': '#ffffff',
    'plot_foreground': '#1c1c1e',
    'scene_muted': '#b8b8bd',       # context geometry behind a selection
    'scene_highlight': '#ff8c2b',   # the selected entity, or the one hovered
    'scene_picked': '#1f9d55',      # nodes gathered so far for a new element
    'row_error': '#c02a1f',         # an object that does not fit the geometry
    # the zones a random-vibration response must not be in: between the
    # warning and abort limits, and beyond abort. Filled translucent, so
    # these are the colours before alpha.
    'limit_warning': '#e6b800',
    'limit_abort': '#d13b2e',
    # the frames a PSD will be averaged over, shaded on the time
    # history they are cut from. The band is translucent, so that is the
    # colour before alpha; the window drawn over each frame is warm on
    # purpose — a blue mark over blue traces reads as another channel
    # a measured line that went outside an abort limit, shaded over its
    # own bin: red where it went over, blue where it fell under. Two
    # colours because which way it went is the first thing to know,
    # and stronger than the zone shading they sit inside
    # a specification and the response it bounds, drawn as a pair: the
    # response in the foreground colour because it is what is being
    # looked at, the specification in grey behind it because it is the
    # reference. Neither takes a palette colour — there is only ever
    # one pair on the plot, so there is nothing to tell apart.
    'response_curve': '#1c1c1e',
    'specification_curve': '#8a8a8f',
    'exceed_over': '#d13b2e',
    'exceed_under': '#2f6fd0',
    'averaging_band': '#3b7dd8',
    'averaging_window': '#c2410c',
    # the filtered trace previewed over the raw one, flat and on the
    # stage alike. **Magenta, measured** (Brandon, 2026-08-25): green
    # was the first choice against the 2-D palette, and it disappeared
    # on the stage — viridis runs purple, teal, *green*, yellow, so a
    # green twin sat inside the very colormap it had to stand out
    # from (49 units from the nearest stop, against magenta's 203).
    # Magenta is in neither the colormap nor the mark colours.
    'filter_preview': '#b5179e',
}

DARK = {
    'name': 'dark',
    'scene_background': '#000000',
    # flat, equal to the base — see the light theme's note
    'scene_background_top': '#000000',
    'scene_text': '#e8e8ea',
    'plot_background': '#000000',
    'plot_background_top': '#000000',
    'plot_foreground': '#e8e8ea',
    'scene_muted': '#4a4a55',       # context geometry behind a selection
    'scene_highlight': '#ffb020',   # the selected entity, or the one hovered
    'scene_picked': '#3ddc84',      # nodes gathered so far for a new element
    'row_error': '#ff6b61',         # an object that does not fit the geometry
    # the zones a random-vibration response must not be in: between the
    # warning and abort limits, and beyond abort. Filled translucent, so
    # these are the colours before alpha.
    'limit_warning': '#ffcc33',
    'limit_abort': '#ff6b61',
    # the frames a PSD will be averaged over, shaded on the time
    # history they are cut from. The band is translucent, so that is the
    # colour before alpha; the window drawn over each frame is warm on
    # purpose — a blue mark over blue traces reads as another channel
    # a measured line that went outside an abort limit, shaded over its
    # own bin: red where it went over, blue where it fell under. Two
    # colours because which way it went is the first thing to know,
    # and stronger than the zone shading they sit inside
    # a specification and the response it bounds, drawn as a pair: the
    # response in the foreground colour because it is what is being
    # looked at, the specification in grey behind it because it is the
    # reference. Neither takes a palette colour — there is only ever
    # one pair on the plot, so there is nothing to tell apart.
    'response_curve': '#ffffff',
    'specification_curve': '#9a9aa2',
    'exceed_over': '#ff6b61',
    'exceed_under': '#5fa8ff',
    'averaging_band': '#5fa8ff',
    'averaging_window': '#fb923c',
    'filter_preview': '#ff5ae0',
}

#: How solid the *other* set is when two mode shapes are overlaid. The
#: basis stays opaque and the comparison is drawn through it: a finite
#: element model has a skin where a test set has a wireframe, and an
#: opaque FEM simply hides the thing it is being compared against.
#:
#: Here rather than in the window because the report draws the same
#: overlay in a canvas and must draw it the same way. It did not, and
#: the difference was invisible until the two were put side by side.
OVERLAY_ALPHA = 0.25

THEMES = {'light': LIGHT, 'dark': DARK}

DEFAULT = 'light'


def theme(name: str | Mapping[str, str] | None = None) -> dict[str, str]:
    """Resolve a theme name (or a colors dict) to a colors dict."""
    if isinstance(name, dict):
        return name
    if name is None:
        return THEMES[DEFAULT]
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(f"Unknown theme {name!r}; choose from {sorted(THEMES)}")


#: viridis, as the nine stops everything interpolates between. One
#: colour scale, one set of numbers: the app paints a moving model by
#: displacement on it, pyqtgraph draws its MAC grids and coherence
#: maps on it, the app icon is drawn with it, and the report is handed
#: these very stops rather than carrying a second copy in JavaScript —
#: so a colour means one thing wherever it appears.
VIRIDIS = ((68, 1, 84), (71, 44, 122), (59, 81, 139), (44, 113, 142),
           (33, 144, 141), (39, 173, 129), (92, 200, 99),
           (170, 220, 50), (253, 231, 37))


def colormap(values: Any) -> Any:
    """`values` in 0..1 as an (N, 3) array of RGB, on `VIRIDIS`."""
    import numpy as np

    stops = np.asarray(VIRIDIS, dtype=float)
    t = np.clip(np.asarray(values, dtype=float), 0.0, 1.0) * (len(stops) - 1)
    low = np.clip(t.astype(int), 0, len(stops) - 2)
    f = (t - low)[..., None]
    return stops[low] * (1.0 - f) + stops[low + 1] * f


def system_scheme(app: Any = None) -> str:
    """'dark' or 'light' from the OS appearance, via Qt.

    Falls back to the default theme when Qt or an application instance is
    unavailable (e.g. plain scripting use).
    """
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return DEFAULT
    app = app or QApplication.instance()
    if app is None:
        return DEFAULT
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return 'dark'
    if scheme == Qt.ColorScheme.Light:
        return 'light'
    palette = app.palette()  # Qt could not tell: judge by palette lightness
    return ('dark' if palette.color(palette.ColorRole.Window).lightness() < 128
            else 'light')
