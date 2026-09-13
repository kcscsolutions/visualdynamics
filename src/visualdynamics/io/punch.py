"""Nastran punch files (.pch) — eigenvectors, read as a ShapeSet.

Phase 2 of the FEM interchange arc (PLAN.md): the bulk deck carries
the mesh and no results, and what a correlation needs is the modes.
SOL 103 punches them as text — `DISPLACEMENT(PUNCH) = ALL` in case
control — in a layout documented in every Nastran vendor's reference
and stable across them, which is exactly why the punch is read and
the .f06 print file is not: the print is a report formatted for eyes
and vendors disagree about its columns; the punch says the same
numbers in a fixed shape.

The layout, from those references: every line is 72 columns of data
with an optional sequence number in 73-80 (dropped unread). A mode
starts at a `$EIGENVALUE = <lambda> MODE = <k>` header — lambda is
the eigenvalue in (rad/s)^2, so the frequency in Hz is
sqrt(lambda)/2pi — under `$` header lines naming the output
(`$DISPLACEMENTS`, `$EIGENVECTOR`) and its arithmetic
(`$REAL OUTPUT` or `$COMPLEX OUTPUT`). Each grid then takes one line
of id, type and three translations, with `-CONT-` lines carrying the
three rotations.

`$COMPLEX OUTPUT` refuses loudly: a complex modal solution punches
its eigenvalue in a header layout no file here has ever shown, and a
guessed frequency on every mode is worse than a refusal naming the
gap — sample-and-extend when a real one arrives.

Only `G` (grid) rows are kept. `S` (scalar) points carry one value
that belongs to no geometric direction, so they are skipped
knowingly rather than mapped onto an axis they do not have.

Real normal modes carry no damping; the ShapeSet says 0 and the
person fitting against it knows why. A punch is unitless like the
deck it came from, so shapes arrive raw.
"""

from __future__ import annotations

import os
import re
from typing import Any

import numpy as np

from .sniffing import text_head

_COMPONENTS = ('X+', 'Y+', 'Z+', 'RX+', 'RY+', 'RZ+')

_MODE_HEADER = re.compile(
    r'\$EIGENVALUE\s*=\s*([-+0-9.ED]+)\s+MODE\s*=\s*(\d+)', re.IGNORECASE)


def sniff(path: str | os.PathLike) -> bool:
    path = str(path)
    if os.path.splitext(path)[1].lower() != '.pch':
        return False
    head = text_head(path)
    return head is not None and bool(_MODE_HEADER.search(head))


def _float(token: str) -> float:
    return float(token.replace('D', 'E').replace('d', 'e'))


def load(path: str | os.PathLike, **_unused: Any) -> Any:
    from ..core.shapes import ShapeSet

    path = str(path)
    with open(path, errors='replace') as f:
        # data lives in columns 1-72; 73-80 is the sequence number
        lines = [line[:72].rstrip('\n') for line in f]

    modes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    row: list[float] | None = None

    for line in lines:
        if line.startswith('$'):
            upper = line.upper()
            if 'COMPLEX OUTPUT' in upper:
                raise ValueError(
                    f'{path}: complex output — the complex punch '
                    'layout has never been seen here and is refused '
                    'rather than guessed; see io/punch.py')
            found = _MODE_HEADER.search(line)
            if found:
                eigenvalue = _float(found.group(1))
                current = {'mode': int(found.group(2)),
                           'eigenvalue': eigenvalue, 'nodes': {}}
                modes.append(current)
            continue
        if current is None or not line.strip():
            continue
        if line.lstrip().startswith('-CONT-'):
            values = [_float(tok) for tok in line.split()[1:]]
            if row is not None:
                row.extend(values)
            continue
        fields = line.split()
        if len(fields) < 2 or not fields[0].lstrip('-').isdigit():
            continue
        node, kind = int(fields[0]), fields[1].upper()
        if kind != 'G':
            row = None          # a scalar point's continuations drop too
            continue
        row = [_float(tok) for tok in fields[2:]]
        current['nodes'][node] = row

    modes = [m for m in modes if m['nodes']]
    if not modes:
        raise ValueError(f'{path}: no eigenvectors in this punch file')

    modes.sort(key=lambda m: m['mode'])
    nodes = list(modes[0]['nodes'])
    for mode in modes:
        if list(mode['nodes']) != nodes:
            raise ValueError(
                f'{path}: modes cover differing grids; a visualdynamics '
                'ShapeSet shares one set of coordinates')

    lengths = {len(row) for mode in modes for row in mode['nodes'].values()}
    if len(lengths) != 1:
        raise ValueError(f'{path}: grid rows carry differing component '
                         f'counts {sorted(lengths)}')
    width = lengths.pop()
    if width not in (3, 6):
        raise ValueError(f'{path}: {width} values per grid fits neither '
                         '3 translations nor 3 with rotations')

    coordinate = [f'{node}{_COMPONENTS[k]}'
                  for node in nodes for k in range(width)]
    shape_matrix = np.array([
        np.concatenate([np.asarray(mode['nodes'][node], dtype=float)
                        for node in nodes])
        for mode in modes])

    frequencies, dampings = [], []
    for mode in modes:
        # lambda = omega^2; a small negative lambda is a rigid body
        # mode reported through numerical noise
        omega = float(np.sqrt(max(mode['eigenvalue'], 0.0)))
        frequencies.append(omega / (2.0 * np.pi))
        dampings.append(0.0)

    # the punch does not record its normalization convention (EIGRL
    # NORM defaults to mass but MAX is common), so the set is marked
    # unscaled: shapes and MACs are unaffected, and nothing downstream
    # reads a physical scale out of modal masses that were never punched
    return ShapeSet(frequency=frequencies, damping=dampings,
                    coordinate=coordinate, shape_matrix=shape_matrix,
                    comment=f'eigenvectors from {os.path.basename(path)}',
                    unscaled=True)
