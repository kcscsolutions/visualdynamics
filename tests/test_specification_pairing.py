"""A specification bounds autospectra; a CPSD carries cross terms too.

Drawn together, the 30 cross terms of a six-channel CPSD are 30 curves with no
limit anywhere near them. They are not wrong — they are just not the
comparison being asked for, and they bury the six that are.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import fixture_path

import visualdynamics
from visualdynamics.plot import bounded_by_specification

pytestmark = pytest.mark.usefixtures('flat_reading')

@pytest.fixture(scope='module')
def spectra():
    return visualdynamics.import_file(fixture_path('plate', 'random_spectra.nc4'))


def counts(series):
    return [len(records) if records is not None else data.num_records
            for _name, data, records in series]


def test_a_cpsd_alone_keeps_every_cross_term(spectra):
    """Nothing is restricted without a specification to restrict against."""
    psd = spectra['Random_response_cpsd']
    kept, dropped = bounded_by_specification([('p', psd, None)])
    assert counts(kept) == [64] and dropped == 0


def test_together_both_are_cut_to_what_they_share(spectra):
    psd, spec = spectra['Random_response_cpsd'], spectra['Random_specification']
    kept, dropped = bounded_by_specification([('s', spec, None), ('p', psd, None)])
    assert counts(kept) == [8, 8]
    assert dropped == 56, 'the cross terms'


def test_what_survives_is_the_diagonal(spectra):
    """The pairs a specification is written for."""
    psd, spec = spectra['Random_response_cpsd'], spectra['Random_specification']
    kept, _dropped = bounded_by_specification([('s', spec, None), ('p', psd, None)])
    _name, data, records = kept[1]
    for record in records:
        assert data.response_dof[record] == data.reference_dof[record]


def test_a_specification_alone_with_a_time_history_restricts_nothing(spectra):
    """There is no other PSD, so there is nothing to intersect against."""
    spec = spectra['Random_specification']
    time = visualdynamics.import_file(fixture_path('plate',
                                         'random.nc4'))['time_data']
    kept, dropped = bounded_by_specification([('s', spec, None),
                                              ('t', time, None)])
    assert counts(kept) == [8, time.num_records] and dropped == 0


def test_a_time_history_is_untouched_even_beside_a_restricted_psd(spectra):
    """A specification says nothing about a time history, so it must not cut
    one — and its channel DOFs *do* match the specification's, so a rule that
    forgot to check the type would quietly drop the drives and look right.

    The previous test cannot catch that: with no other PSD present the whole
    restriction short-circuits before the type is ever examined.
    """
    spec = spectra['Random_specification']
    psd = spectra['Random_response_cpsd']
    time = visualdynamics.import_file(fixture_path('plate',
                                         'random.nc4'))['time_data']
    kept, dropped = bounded_by_specification(
        [('s', spec, None), ('p', psd, None), ('t', time, None)])
    assert counts(kept) == [8, 8, time.num_records]
    assert dropped == 56, 'the cross terms, and nothing from the time data'
    # the measured entry may come back renamed for its comparison
    # scaling; what matters here is that the time history is untouched
    assert [name.split(' (')[0] for name, _d, _r in kept] == ['s', 'p', 't']
    assert kept[2][1] is time, 'the time history is the very object'


def test_an_autospectrum_with_no_reference_pairs_with_the_diagonal(spectra):
    """A PSD need not carry reference DOFs at all; a record without one is a
    channel against itself, which is exactly what a specification bounds."""
    from visualdynamics.core.data import Psd

    spec = spectra['Random_specification']
    asds = Psd(abscissa=spec.abscissa,
               ordinate=np.ones((2, len(spec.abscissa))),
               response_dof=[spec.response_dof[0], '999Z+'],
               ordinate_dim='acceleration**2/frequency',
               ordinate_unit='m/s**2')
    kept, dropped = bounded_by_specification([('s', spec, None),
                                              ('a', asds, None)])
    # symmetric: the specification loses the seven channels this PSD
    # does not measure, and the PSD loses the one the specification
    # does not bound
    assert counts(kept) == [1, 1]
    assert dropped == 8
    _name, data, records = kept[1]
    assert [data.response_dof[i] for i in records] == [spec.response_dof[0]]


def test_a_record_subset_is_respected(spectra):
    """Restricting starts from what was asked for, not from the whole object."""
    psd, spec = spectra['Random_response_cpsd'], spectra['Random_specification']
    diagonal = [i for i, (r, c) in enumerate(zip(psd.response_dof,
                                                 psd.reference_dof)) if r == c]
    kept, dropped = bounded_by_specification(
        [('s', spec, None), ('p', psd, diagonal[:2])])
    assert counts(kept) == [2, 2], 'the specification narrows to match'
    assert dropped == 6, 'the six specification channels not asked for'


def test_nothing_in_common_restricts_nothing(spectra):
    """Incompatibility warns, it does not block. Cutting both sides to
    nothing would leave an empty plot; drawing them makes the mismatch
    visible, which is the useful answer."""
    from visualdynamics.core.data import Psd

    spec = spectra['Random_specification']
    elsewhere = Psd(abscissa=spec.abscissa,
                    ordinate=np.ones((1, len(spec.abscissa))),
                    response_dof=['999Z+'],
                    ordinate_dim='acceleration**2/frequency',
                    ordinate_unit='m/s**2')
    kept, dropped = bounded_by_specification([('s', spec, None),
                                              ('e', elsewhere, None)])
    assert [name for name, _d, _r in kept] == ['s', 'e']
    assert counts(kept) == [8, 1]
    assert dropped == 0


def test_the_window_says_what_it_hid(window, pump):
    window.import_paths([fixture_path('plate', 'random_spectra.nc4')])
    window.tree.clearSelection()
    for name in ('PSD', 'Specification'):
        window._item_for_object(name).setSelected(True)
    pump()
    message = window.statusBar().currentMessage()
    # two: one comparison is drawn at a time now, and the bar offers the
    # rest. What the specification could not bound is still reported.
    assert '2 curves' in message
    assert '56 records hidden' in message


def test_a_drive_points_force_spectrum_is_not_compared(spectra):
    """A drive that is also a control channel carries a force PSD under
    the same DOF name as its acceleration — and a specification for
    accelerations says nothing about newtons. The force records hide
    with the other unmatched ones."""
    from visualdynamics.core.data import Psd

    spec = spectra['Random_specification']
    psd = spectra['Random_response_cpsd']
    diagonal = [i for i, (r, c) in enumerate(zip(psd.response_dof,
                                                 psd.reference_dof))
                if r == c]
    forces = Psd(abscissa=psd.abscissa,
                 ordinate=np.ones((2, len(psd.abscissa))),
                 response_dof=[spec.response_dof[0], spec.response_dof[1]],
                 ordinate_dim='force**2/frequency',
                 ordinate_unit='N')
    kept, dropped = bounded_by_specification(
        [('s', spec, None), ('p', psd, diagonal), ('f', forces, None)])
    assert [name for name, _d, _r in kept] == ['s', 'p'], (
        'the force spectra vanish from the comparison entirely')
    assert dropped == 2
