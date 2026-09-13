"""The four scriptable faces `test_headless.py` names as strings and
nothing called: each view the app draws has a plain-Python call that
draws the same thing to a file, and a name in an inventory is not a
promise kept. Each is run here, off screen, and has to leave a
picture behind."""

from __future__ import annotations

from test_banded_stage import _measured, _specification
from test_paired_stage import _pair
from test_sine import _spec, _tone


def _picture(path):
    assert path.exists() and path.stat().st_size > 1000, path


def test_plot_ratio_draws_to_a_file(tmp_path):
    from visualdynamics.plot import plot_ratio

    loud, quiet = _pair()
    out = tmp_path / 'ratio.png'
    plot_ratio(loud, quiet, path=out, show=False)
    _picture(out)


def test_plot_banded_stage_draws_to_a_file(tmp_path):
    from visualdynamics.viz.banded import plot_banded_stage

    out = tmp_path / 'stage.png'
    plot_banded_stage(_specification(), _measured(), screenshot=str(out),
                      show=False)
    _picture(out)


def test_plot_paired_stage_draws_to_a_file(tmp_path):
    from visualdynamics.viz.paired import plot_paired_stage

    loud, quiet = _pair()
    for mode in ('overlay', 'ratio'):
        out = tmp_path / f'{mode}.png'
        plot_paired_stage(loud, quiet, mode, screenshot=str(out), show=False)
        _picture(out)


def test_plot_sine_specification_draws_to_a_file(tmp_path):
    from visualdynamics.viz.sinespec import plot_sine_specification

    out = tmp_path / 'sine.png'
    plot_sine_specification(_spec(_tone()), screenshot=str(out), show=False)
    _picture(out)
