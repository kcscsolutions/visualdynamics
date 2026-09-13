"""An SRS reads in decades of natural frequency, on every surface.

Reviewer feedback (Brandon, 2026-08-25): SRS plots are conventionally
viewed on log frequency axes. One flag on the class —
`Srs.log_abscissa` — read by the 2-D plot, the 3-D stage and the
report, so the three renderers cannot disagree about the layout: the
same discipline as `log_scaled()` on the vertical axis.
"""

from __future__ import annotations

import numpy as np
import pytest

import visualdynamics
from visualdynamics.core import srs as srs_module
from visualdynamics.core.data import Psd, ShockSpecification, Srs, TimeHistory

_ALIVE: list = []


def _srs(channels=2):
    frequencies = srs_module.octave_frequencies(20.0, 2000.0)
    values = 10.0 * (frequencies / 20.0) ** 0.5
    return Srs(frequencies, np.tile(values, (channels, 1)),
               response_dof=[f'{101 + i}Z+' for i in range(channels)],
               ordinate_dim='acceleration', ordinate_unit='m/s**2')


def _specification():
    frequencies = srs_module.octave_frequencies(20.0, 2000.0)
    required = 10.0 * (frequencies / 20.0) ** 0.5
    return ShockSpecification(
        abscissa=frequencies, ordinate=np.atleast_2d(required),
        response_dof=['101Z+'], ordinate_dim=['acceleration'],
        abort_upper=np.atleast_2d(required * 2.0),
        abort_lower=np.atleast_2d(required * 0.5))


# ---- the flag ------------------------------------------------------------


def test_the_srs_reads_in_decades_and_nothing_else_does():
    assert Srs.log_abscissa
    assert ShockSpecification.log_abscissa, \
        'a shock specification is an SRS in every axis respect'
    assert not Psd.log_abscissa
    assert not TimeHistory.log_abscissa


# ---- the 2-D plot --------------------------------------------------------


def _plots(series):
    import pyqtgraph as pg

    from visualdynamics.plot import build_plots

    layout = pg.GraphicsLayoutWidget()
    _ALIVE.append(layout)
    build_plots(layout, series)
    return [item for item in layout.ci.items
            if hasattr(item, 'listDataItems')]


def test_the_flat_plot_goes_log_in_x_for_an_srs(qt_app):
    (plot,) = _plots([('SRS', _srs(), None)])
    assert plot.getAxis('bottom').logMode, 'decades across'
    assert plot.getAxis('left').logMode, 'and the level stays log too'
    (linear,) = _plots([('Time', TimeHistory(
        np.arange(256) / 256.0, np.ones((1, 256)),
        response_dof='101Z+', ordinate_dim='acceleration'), None)])
    assert not linear.getAxis('bottom').logMode


def test_the_comparison_keeps_its_band_in_the_same_space(qt_app):
    """The zone fills are built from plot.plot curves precisely so the
    axis's log space carries them — in x now as well as y."""
    import pyqtgraph as pg

    (plot,) = _plots([('Spec', _specification(), None),
                      ('SRS', _srs(1), None)])
    assert plot.getAxis('bottom').logMode
    fills = [item for item in plot.items
             if isinstance(item, pg.FillBetweenItem)]
    assert fills, 'the tolerance band survived the log axis'


def test_a_log_x_plot_never_links_to_a_linear_one(qt_app):
    """Both are 'frequency', but a log-x view and a linear one share
    coordinates in name only — linked, panning one slaved real
    frequencies to their own logarithms."""
    frequencies = np.linspace(1.0, 100.0, 64)
    psd = Psd(frequencies, np.ones((1, 64)), response_dof='101Z+',
              ordinate_dim='acceleration**2/frequency',
              ordinate_unit='(m/s**2)**2/Hz')
    plots = _plots([('SRS', _srs(1), None), ('PSD', psd, None)])
    assert len(plots) == 2
    linked = [plot.getViewBox().linkedView(0) for plot in plots]
    assert not any(linked), 'two scales, two independent x views'


# ---- the 3-D stage -------------------------------------------------------


def test_the_stage_stands_in_log10_of_natural_frequency():
    from visualdynamics.viz.waterfall import waterfall_arrays

    data = _srs()
    arrays = waterfall_arrays(data, unit_system=visualdynamics.SI)
    assert arrays['log_abscissa']
    cx = arrays['curves'][0][0]
    assert cx[0] == pytest.approx(np.log10(20.0), abs=1e-6)
    assert cx[-1] == pytest.approx(np.log10(float(data.abscissa[-1])),
                                   abs=1e-6)
    assert arrays['xlabel'].startswith('log10 '), \
        "VTK prints the coordinates as they are, so the title says so"
    flat = waterfall_arrays(
        TimeHistory(np.arange(256) / 256.0, np.ones((1, 256)),
                    response_dof='101Z+', ordinate_dim='acceleration'),
        unit_system=visualdynamics.SI)
    assert not flat['log_abscissa']


# ---- the report ----------------------------------------------------------


def test_every_report_figure_of_an_srs_reads_in_decades():
    from visualdynamics.report import _build_block

    objects = {'SRS': _srs(1), 'Spec': _specification()}
    us = visualdynamics.SI

    flat = _build_block({'kind': 'plot', 'source': 'SRS',
                         'mode': 'curves', 'caption': 'c'}, objects, us, [])
    assert flat['logx']
    assert flat['x'][0] == pytest.approx(np.log10(20.0), abs=1e-6)

    comparison = _build_block(
        {'kind': 'plot', 'source': 'SRS', 'mode': 'curves',
         'specification': 'Spec', 'caption': 'c'}, objects, us, [])
    assert comparison['logx']
    assert comparison['x'][0] == pytest.approx(np.log10(20.0), abs=1e-6)

    banded = _build_block({'kind': 'plot', 'source': 'Spec',
                           'mode': 'curves', 'caption': 'c'},
                          objects, us, [])
    assert banded['logx'], 'the requirement alone reads the same way'

    stage = _build_block({'kind': 'plot', 'source': 'SRS',
                          'mode': 'stage', 'caption': 'c'}, objects, us, [])
    stage = stage[0] if isinstance(stage, list) else stage
    assert stage['logx']
    assert not stage['xlabel'].startswith('log10'), \
        'the canvas prints real values at decade ticks, so no prefix'
    x0, _x1, _z0, _z1 = stage['extents']
    assert x0 == pytest.approx(np.log10(20.0), abs=1e-3)

    # and the page draws both x-tick sites through the flag — the same
    # counted-occurrence pin the z axis carries
    from visualdynamics.report.page import _JS

    assert _JS.count('ticks(view.x0, view.x1, block.logx)') == 1
    assert _JS.count('ticks(x0, x1, block.logx)') == 1
    assert 'ticks(view.x0, view.x1, false)' not in _JS
    assert 'ticks(x0, x1, false)' not in _JS


def test_a_time_figure_stays_linear_in_x():
    from visualdynamics.report import _build_block

    history = TimeHistory(np.arange(256) / 256.0, np.ones((1, 256)),
                          response_dof='101Z+',
                          ordinate_dim='acceleration')
    built = _build_block({'kind': 'plot', 'source': 'T',
                          'mode': 'curves', 'caption': 'c'},
                         {'T': history}, visualdynamics.SI, [])
    assert not built['logx']
    assert built['x'][0] == pytest.approx(0.0)


def test_the_banded_stage_draws_band_and_ribbons_in_one_space():
    """Brandon saw it on sight (2026-08-25): the measured ribbons came
    off `waterfall_arrays` in decades while the specification band
    stayed in hertz, which put the whole measurement in the left
    margin of its own requirement. Everything drawn shares one x
    space; the exceedances are still *judged* in real frequency."""
    from visualdynamics.core import srs as srs_module
    from visualdynamics.viz.banded import banded_stage_arrays

    frequencies = srs_module.octave_frequencies(20.0, 2000.0)
    required = 10.0 * (frequencies / 20.0) ** 0.5
    spec = ShockSpecification(
        abscissa=frequencies, ordinate=np.atleast_2d(required),
        response_dof=['101Z+'], ordinate_dim=['acceleration'],
        abort_upper=np.atleast_2d(required * 2.0),
        abort_lower=np.atleast_2d(required * 0.5))
    over = Srs(frequencies, np.atleast_2d(required * 3.0),
               response_dof=['101Z+'], ordinate_dim='acceleration',
               ordinate_unit='m/s**2', block=['event 1'])
    arrays = banded_stage_arrays(spec, over,
                                 unit_system=visualdynamics.SI)
    station = arrays['stations'][0]
    curve_x = np.asarray(station['curves'][0]['x'])
    drawn_spec = arrays['spread'](arrays['spec_x'])
    assert curve_x[0] == pytest.approx(np.log10(20.0), abs=1e-9)
    assert drawn_spec[0] == pytest.approx(curve_x[0], abs=1e-9), \
        'the band opens where the measurement opens'
    assert drawn_spec[-1] == pytest.approx(curve_x[-1], abs=1e-9)
    assert station['exceed'], 'three times the requirement is out'
    assert station['exceed'][0]['out'].any()
    assert arrays['xlabel'].startswith('log10 ')

    alone = banded_stage_arrays(spec, unit_system=visualdynamics.SI)
    assert alone['spread'](alone['spec_x'])[0] == pytest.approx(
        np.log10(20.0), abs=1e-9), 'the requirement alone reads the same'
    assert alone['xlabel'].startswith('log10 ')

    # and in the *drawn* scene, not just the arrays: the first pin
    # passed with the drawing still mixing spaces, because it never
    # asked the plotter. The band mesh and the measured mesh must
    # cover the same x on the stage — a band drawn in hertz over a
    # ribbon in decades spans ~2000 stage units against its ~2.
    import pyvista as pv

    from visualdynamics.viz.banded import add_banded_stage

    plotter = pv.Plotter(off_screen=True)
    add_banded_stage(plotter, spec, over, unit_system=visualdynamics.SI)
    meshes = {name: actor.mapper.dataset
              for name, actor in plotter.actors.items()
              if 'banded-0' in name and hasattr(actor, 'mapper')}
    band = next(m for name, m in meshes.items() if 'zone' in name)
    ribbon = next(m for name, m in meshes.items() if 'measured' in name)
    for axis in (0,):
        band_span = band.bounds[1] - band.bounds[0]
        ribbon_span = ribbon.bounds[1] - ribbon.bounds[0]
    assert band_span == pytest.approx(ribbon_span, rel=0.01), \
        'the band and the measurement stand on one x axis'
    plotter.close()
