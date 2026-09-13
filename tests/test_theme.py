
import pytest
from conftest import fixture_path

import visualdynamics
from visualdynamics import theme as theme_module

PLATE = fixture_path('plate', 'geometry.exo')


def test_theme_names():
    assert set(theme_module.THEMES) == {'light', 'dark'}
    assert theme_module.theme('dark')['name'] == 'dark'
    assert theme_module.theme()['name'] == theme_module.DEFAULT


def test_theme_accepts_colors_dict():
    colors = theme_module.DARK
    assert theme_module.theme(colors) is colors


def test_unknown_theme_raises():
    with pytest.raises(ValueError):
        theme_module.theme('solarized')


def test_system_scheme_without_qt_app():
    """Scripting use with no QApplication falls back rather than failing."""
    assert theme_module.system_scheme() in ('light', 'dark')


def test_system_scheme_reads_the_apps_own_hint(qt_app):
    """With an application up — the startup path since apply_theme runs
    at launch — the answer comes from Qt's scheme, not the default."""
    from PySide6.QtCore import Qt

    got = theme_module.system_scheme(qt_app)
    scheme = qt_app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        assert got == 'dark'
    elif scheme == Qt.ColorScheme.Light:
        assert got == 'light'
    else:
        assert got in ('light', 'dark'), 'judged by palette lightness'


def test_system_scheme_judges_by_palette_when_qt_cannot_say():
    """Qt reports Unknown on platforms without a scheme signal; the
    window's background lightness is the honest fallback."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette

    class Hints:
        def colorScheme(self):
            return Qt.ColorScheme.Unknown

    class FakeApp:
        def __init__(self, window_color):
            self._palette = QPalette()
            self._palette.setColor(QPalette.ColorRole.Window,
                                   QColor(window_color))
        def styleHints(self):
            return Hints()
        def palette(self):
            return self._palette

    assert theme_module.system_scheme(FakeApp('#101010')) == 'dark'
    assert theme_module.system_scheme(FakeApp('#f0f0f0')) == 'light'


def test_scene_background_follows_theme():
    import pyvista as pv

    from visualdynamics.viz.geometry import geometry_scene

    geometry = visualdynamics.import_file(PLATE, length_unit='m')
    for name in ('light', 'dark'):
        plotter = pv.Plotter(off_screen=True)
        geometry_scene(geometry, plotter=plotter, theme=name)
        expected = pv.Color(theme_module.THEMES[name]['scene_background'])
        assert plotter.background_color == expected
        plotter.close()
