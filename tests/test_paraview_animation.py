"""The exodus we write is the exodus ParaView animates.

Not a round trip — `test_export.py` owns those. This is the other half:
a file we can read back perfectly can still be one ParaView cannot use,
and the ways that happens are silent. Both of the ones pinned here were
found by driving the real pipeline rather than by reading the file.

ParaView animates a modal exodus with **Animate Modes**
(`vtkAnimateModes`), reading it through **vtkIOSSReader**. VTK ships
both classes and pyvista already brings VTK, so the check costs no new
dependency and asks the actual consumer instead of a model of it.

Two things have to hold, and neither is visible in a round trip because
our own reader is forgiving about both:

1. **One time step per mode, its frequency as the time.** Coincident
   frequencies collapse — six rigid-body modes at exactly 0 Hz arrive as
   one time step and five modes vanish — which is why the writer nudges
   them a hair apart.
2. **One stem, then `X`/`Y`/`Z`** — `DispX`/`DispY`/`DispZ`. IOSS joins
   components on a shared stem with those three suffixes into a single
   three-component `Disp` vector, and a vector is what Animate Modes
   needs for its input array. Named without that shape — `D1`/`D2`/`D3`,
   or a stem that does not match across the three — the file still
   loads, still reads back into visualdynamics, and offers ParaView
   three unrelated scalars it cannot animate.

   Measured rather than assumed, because the obvious guesses were
   wrong in both directions. IOSS is *more* forgiving than expected
   about the separator and the case — `Disp_X`, `disp_x` and `DISPX`
   all join, as does `Ux`/`Uy`/`Uz` — and completely unforgiving about
   the suffix: `DispX`/`DispY`/`DispQ` joins nothing. So this test
   guards the stem-and-XYZ shape, not the exact spelling.

A third fact is ParaView's rather than ours, and is worth writing down
because it looks like a bug in the file: `vtkAnimateModes` publishes a
*continuous* time range 0..1 and no discrete time steps of its own. An
animation snapping to time steps therefore falls back to the only
discrete ones in the pipeline — the reader's, which are the mode
frequencies. The cure is a Sequence of frames over 0..1, and nothing
about the export changes it.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import fixture_path

import visualdynamics


def survey(name: str) -> str:
    return fixture_path('plate', name)


@pytest.fixture(scope='module')
def source() -> tuple:
    """The survey's 64 modes — six of them at coincident frequencies,
    which is what makes the nudge worth testing."""
    shapes = visualdynamics.import_file(survey('shapes.npy'), mass_unit='kg')
    return shapes, visualdynamics.import_file(survey('geometry.npz'))


@pytest.fixture(scope='module')
def written(source, tmp_path_factory) -> str:
    shapes, mesh = source
    path = str(tmp_path_factory.mktemp('paraview') / 'modes.exo')
    visualdynamics.io.exodus.save(shapes, path, geometry=mesh)
    return path


@pytest.fixture(scope='module')
def reader(written):
    """The file through ParaView's own reader, information updated."""
    from vtkmodules.vtkIOIOSS import vtkIOSSReader

    r = vtkIOSSReader()
    r.SetFileName(written)
    r.UpdateInformation()
    return r


def timesteps(algorithm) -> list[float]:
    from vtkmodules.vtkCommonExecutionModel import (
        vtkStreamingDemandDrivenPipeline as SDDP,
    )

    found = algorithm.GetOutputInformation(0).Get(SDDP.TIME_STEPS())
    return [] if found is None else list(found)


def first_leaf(algorithm):
    """The one block of a partitioned dataset — the mesh itself."""
    out = algorithm.GetOutputDataObject(0)
    walk = out.NewIterator()
    walk.InitTraversal()
    return walk.GetCurrentDataObject()


def test_every_mode_is_its_own_time_step_at_its_own_frequency(reader, source):
    """The nudge, from ParaView's side of it.

    Written without it, the survey's four modes at 0 Hz and two at
    1e-4 Hz come back as two time steps rather than six, and the modes
    in between are simply not in the file as far as ParaView is
    concerned. Our own reader never notices: it reads the values, not
    the time axis.
    """
    shapes, _mesh = source
    times = timesteps(reader)
    assert len(times) == shapes.num_shapes, (
        f'{len(times)} time steps for {shapes.num_shapes} modes — '
        'coincident frequencies have collapsed')
    assert len(set(times)) == len(times), 'two modes share a time step'
    # the nudge is a hair: a thousand-millionth of the top frequency, so
    # what ParaView labels each step with is still the frequency
    assert np.allclose(times, shapes.frequency, atol=1e-3)
    assert times == sorted(times), 'time has to run forwards'


def test_the_displacements_arrive_as_one_vector_not_three_scalars(reader):
    """The component naming is not cosmetic: a shared stem with X/Y/Z
    suffixes is what IOSS joins into a vector, and Animate Modes takes a
    vector. `D1`/`D2`/`D3` arrives as three scalars and animates
    nothing."""
    reader.Update()
    point_data = first_leaf(reader).GetPointData()
    arrays = {point_data.GetArray(i).GetName():
              point_data.GetArray(i).GetNumberOfComponents()
              for i in range(point_data.GetNumberOfArrays())}
    assert arrays.get('Disp') == 3, (
        f'ParaView sees {arrays} — it needs a 3-component "Disp" to '
        'animate, and gets one only when the three components share a '
        'stem and end in X, Y and Z')


def test_paraview_animates_the_modes_it_finds(reader, source):
    """The whole point of the file, driven the way the filter drives it.

    `ModeShape` is 1-based and indexes the time steps, so the count the
    filter offers is the count of modes that survived the write — the
    same thing the first test asserts, asked of the filter instead of
    the reader.
    """
    from vtkmodules.util.numpy_support import vtk_to_numpy
    from vtkmodules.vtkCommonDataModel import vtkDataObject
    from vtkmodules.vtkFiltersGeneral import vtkAnimateModes

    shapes, _mesh = source
    animate = vtkAnimateModes()
    animate.SetInputConnection(reader.GetOutputPort())
    animate.SetInputArrayToProcess(
        0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, 'Disp')
    animate.SetAnimateVibrations(True)
    animate.SetModeShape(shapes.num_shapes)      # the highest one written
    animate.UpdateInformation()

    assert animate.GetModeShapesRange() == (1, shapes.num_shapes)

    def points(phase: float) -> np.ndarray:
        animate.UpdateTimeStep(phase)
        return vtk_to_numpy(first_leaf(animate).GetPoints().GetData()).copy()

    start, quarter, half = points(0.0), points(0.25), points(0.5)
    assert not np.allclose(start, half), (
        'the mesh does not move over the cycle — the mode reached '
        'ParaView with no displacement in it')
    assert np.allclose(start, points(1.0)), 'the cycle does not close'
    # 0 -> 0.5 is the swing, and a quarter of the way is partway along
    # it: enough to say the motion is graded rather than a jump
    assert 0.0 < np.abs(quarter - start).max() < np.abs(half - start).max()
