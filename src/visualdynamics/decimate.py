"""Peak-keeping decimation: fewer points, every peak kept.

A million-sample record cannot go to a renderer point for point, and
plain striding is the wrong thinning: it walks straight past the one
spike that was the reason to look at the record. The peak-keeping
reading cuts the samples into equal slices and keeps each slice's
smallest and largest value at their own abscissa positions, so no
resonance, dropout or shock thins away — the same reading pyqtgraph's
`peak` downsampling gives the 2-D plot.

One implementation, used by the report (a document, not a scope) and
by the 3-D waterfall (a scene with a point budget). The core is
vectorized over whole records at once because the waterfall hands it
hundreds of them: as a per-bin Python loop the same work took 10.6 s
on a 320-record million-sample history, batched it is 1.3 s — both
measured. numpy only.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def peak_decimate(x: ArrayLike, y: ArrayLike,
                  budget: int) -> tuple[np.ndarray, np.ndarray]:
    """(x, y) thinned to about `budget` points that keep every extreme.

    Real values; a caller reading complex data extracts its component
    first, because "the extremes" of a complex value is not a question
    with one answer. Input at or under the budget is returned as given.

    NaN marks a gap (a specification is NaN outside its band) and never
    wins an extreme. A slice that is *all* gap keeps its first point, so
    the gap survives to be drawn as a gap.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    if len(x) <= budget:
        return x, y
    keep = _extreme_indices(y[np.newaxis], budget // 2)[0]
    return x[keep], y[keep]


def peak_decimate_rows(x: ArrayLike, rows: ArrayLike,
                       budget: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """`peak_decimate` for every record of one object at once.

    The records share `x` going in but not coming out: each keeps its
    own extremes at their own positions. One vectorized pass over the
    whole (records, samples) block, which is what makes decimating a
    320-record million-sample history cost tenths of a second rather
    than tens.
    """
    x = np.asarray(x)
    rows = np.atleast_2d(np.asarray(rows))
    if rows.shape[1] <= budget:
        return [(x, rows[k]) for k in range(rows.shape[0])]
    kept = _extreme_indices(rows, budget // 2)
    return [(x[keep], rows[k][keep]) for k, keep in enumerate(kept)]


def _extreme_indices(rows: np.ndarray, bins: int) -> list[np.ndarray]:
    """Per record, the sorted sample indices keeping each slice's extremes.

    Slices are a uniform chunk with the tail padded, rather than
    `linspace` edges, because a uniform chunk is what one `reshape`
    and one `argmin` over the whole block can answer — the per-bin
    Python loop this replaces was the entire cost of a large
    waterfall. Infinities stand in for NaN during the argmin/argmax
    so an all-gap slice cannot raise; such a slice keeps its first
    sample instead, and the gap survives.
    """
    n, m = rows.shape
    chunk = -(-m // bins)
    padded = np.full((n, bins * chunk), np.nan)
    padded[:, :m] = rows
    shaped = padded.reshape(n, bins, chunk)
    finite = np.isfinite(shaped)
    any_finite = finite.any(axis=-1)
    lo = np.argmin(np.where(finite, shaped, np.inf), axis=-1)
    hi = np.argmax(np.where(finite, shaped, -np.inf), axis=-1)
    starts = np.arange(bins) * chunk
    # an all-gap slice keeps its start; slices entirely in the padding
    # (starts past the data) are dropped below
    lo = starts + np.where(any_finite, lo, 0)
    hi = starts + np.where(any_finite, hi, 0)
    real = starts < m
    return [np.unique(np.concatenate([row_lo[real], row_hi[real]]))
            for row_lo, row_hi in zip(lo, hi)]
