"""Importer for sdynpy data array files (.npz).

The format is a numpy .npz with two entries:

- 'function_type': scalar int, UFF dataset 58 function type code (the same
  vocabulary visualdynamics uses: 1 time response, 4 FRF, 9 PSD, 12 spectrum)
- 'data': structured array with per-record fields 'abscissa' (n,), 'ordinate'
  (n,), 'comment1'..'comment5', and 'coordinate' — (node, direction) pairs,
  shape (1,) for response-only data or (2,) for response/reference data.
  Directions use the UFF signed 1..6 code.

Files carry no units. Units may be declared at import:

- time/spectrum data:   ordinate_unit (e.g. 'm/s**2', 'g', 'N')
- FRF:                  response_unit and reference_unit
- PSD:                  ordinate_unit = the engineering unit whose square-
                        per-Hz the PSD is in (e.g. 'g' for g^2/Hz)

Without them the data arrives unit-less, holding the file's raw values, for
the user to define units later with `define_units()`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                                    # pragma: no cover
    from ..core.data import DataArray
    from ..units import UnitSystem

import numpy as np

from ..core.data import (
    DataArray,
    Frf,
    class_for_function_type,
    direction_code,
    dof_string,
    parse_dof,
)
from .sniffing import npz_has


def sniff(path: str | os.PathLike) -> bool:
    return npz_has(path, {'data', 'function_type'})


def load(path: str | os.PathLike, ordinate_unit: str | None = None,
         response_unit: str | None = None,
         reference_unit: str | None = None) -> DataArray:
    with np.load(path, allow_pickle=True) as d:
        function_type = int(d['function_type'])
        data = d['data']

    cls = class_for_function_type(function_type)
    data = data.reshape(-1)

    abscissa = data['abscissa']
    if not np.allclose(abscissa, abscissa[0]):
        raise ValueError(f'Records in {path} have differing abscissae; '
                         'visualdynamics data arrays share one abscissa')

    coordinate = data['coordinate']
    response_dof = [dof_string(c['node'][0], c['direction'][0])
                    for c in coordinate]
    reference_dof = None
    if coordinate.shape[-1] > 1:
        reference_dof = [dof_string(c['node'][1], c['direction'][1])
                         for c in coordinate]

    comments = ['; '.join(s for i in range(1, 6)
                          if (s := str(rec[f'comment{i}']).strip()))
                for rec in data]

    array = cls(
        abscissa=abscissa[0],
        ordinate=np.stack(list(data['ordinate'])),
        response_dof=response_dof,
        reference_dof=reference_dof,
        comment=comments,
    )

    if cls is Frf:
        if response_unit is not None and reference_unit is not None:
            array.define_units(response_unit, reference_unit)
    elif ordinate_unit is not None:
        array.define_units(ordinate_unit)
    return array


def handles(obj: Any) -> bool:
    return isinstance(obj, DataArray)


def _coordinate_pairs(data):
    """(node, direction) per record, paired when the data names a reference.

    Not only FRFs: a PSD names the pair it was formed from, and writing one
    entry would quietly drop the reference on the way out.
    """
    width = 2 if data.reference_dof is not None else 1
    pairs = np.zeros((data.num_records, width),
                     dtype=[('node', '<u8'), ('direction', 'i1')])
    for i in range(data.num_records):
        node, direction = parse_dof(data.response_dof[i])
        pairs[i, 0] = (node or 0, direction_code(direction) if direction else 0)
        if width == 2:
            node, direction = parse_dof(data.reference_dof[i])
            pairs[i, 1] = (node or 0,
                           direction_code(direction) if direction else 0)
    return pairs


def save(data: DataArray, path: str | os.PathLike, unit_system: UnitSystem | None = None) -> None:
    """Write a data array in sdynpy's own .npz layout.

    Values go out in `unit_system`, or as stored without one. The format
    has nowhere to record which units they are.
    """
    from .exporters import data_values

    abscissa, ordinate = data_values(data, unit_system)
    samples = len(abscissa)
    # complex only for data that is: a real time history written as
    # '<c16' doubles the file and comes back through the constructor
    # with a ComplexWarning, which is sdynpy's own convention anyway —
    # its writer stores each array in the ordinate's true dtype
    dtype = [('abscissa', '<f8', (samples,)),
             ('ordinate',
              '<c16' if np.iscomplexobj(ordinate) else '<f8', (samples,)),
             *[(f'comment{i}', '<U80') for i in range(1, 6)],
             ('coordinate', [('node', '<u8'), ('direction', 'i1')],
              (2 if data.reference_dof is not None else 1,))]
    records = np.zeros(data.num_records, dtype=dtype)
    records['abscissa'] = abscissa
    records['ordinate'] = ordinate
    records['coordinate'] = _coordinate_pairs(data)
    np.savez(path, data=records,
             function_type=np.array(data.function_type))
