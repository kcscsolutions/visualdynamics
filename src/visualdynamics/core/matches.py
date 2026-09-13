"""Matched mode pairs between two shape sets.

The user picks MAC squares and commits them; the matches are a project
object of their own — saveable, renameable, deletable row by row — not
a report's private note. The sets are referenced by name and read live
wherever the matches are shown, but the MAC values are stored with the
picks: they came from the comparison as displayed, projected onto the
basis DOFs when the geometries demanded it, and a name-matched
recompute would not reproduce them.
"""

from __future__ import annotations

from collections.abc import Sequence


class MatchedModes:
    """Pairs of (first-set mode, second-set mode) with their MAC.

    `first` and `second` name shape sets in the project; the first is
    the comparison's basis — its frequencies are the Δf% baseline.

    Committing the squares picked on a cross-MAC makes one of these, so
    the pairing is a thing in the project rather than a state of the
    window: a report binds to it by name, and reopening the project finds
    the same pairs.

    Attributes:
        first: The name of the set whose modes are the rows, and whose
            frequencies the Δf% is measured from.
        second: The name of the set whose modes are the columns.
        pairs: `[row mode, column mode]` per committed pair, zero-based.
        macs: The MAC of each pair, as it was computed when committed —
            possibly after projecting onto the basis DOFs, which is why
            it is stored rather than recomputed.
        first_geometry: The geometry `first` was linked to at the time,
            since a projection is only meaningful against it.
        second_geometry: The same for `second`.
    """

    def __init__(self, first: str, second: str,
                 pairs: Sequence[Sequence[int]] | None = None,
                 macs: Sequence[float] | None = None,
                 first_geometry: str | None = None,
                 second_geometry: str | None = None) -> None:
        self.first: str = str(first)
        self.second: str = str(second)
        self.pairs: list[list[int]] = [[int(row), int(column)]
                      for row, column in (pairs or [])]
        self.macs: list[float] = [float(mac) for mac in (macs or [])]
        # the geometries each set was linked to when the matches were
        # committed — what an overlaid animation of the pair deflects
        self.first_geometry: str | None = str(first_geometry) if first_geometry \
            else None
        self.second_geometry: str | None = str(second_geometry) if second_geometry \
            else None
        self._sort()

    def _sort(self) -> None:
        """Matches in the first set's own order, which is by frequency.

        A matched table is read down the page against the mode list
        beside it, and pairs land in it in the order squares were
        clicked on the MAC — which is the order somebody's eye moved,
        not an order. Sorting by the first set's mode index is sorting
        by its frequency, because a `ShapeSet` is always in frequency
        order; doing it that way needs no lookup of a set that may not
        be in the project any more.

        The second index breaks ties, so one mode matched to two of the
        other set reads low to high rather than by which was clicked
        first.
        """
        order = sorted(range(len(self.pairs)),
                       key=lambda i: (self.pairs[i][0], self.pairs[i][1]))
        self.pairs = [self.pairs[i] for i in order]
        self.macs = [self.macs[i] for i in order]

    @property
    def num_matches(self) -> int:
        return len(self.pairs)

    def add(self, pairs: Sequence[Sequence[int]],
            macs: Sequence[float]) -> None:
        """Add matches, restating the MAC of any pair already here."""
        for pair, mac in zip(pairs, macs):
            pair = [int(pair[0]), int(pair[1])]
            if pair in self.pairs:
                self.macs[self.pairs.index(pair)] = float(mac)
            else:
                self.pairs.append(pair)
                self.macs.append(float(mac))
        self._sort()

    def delete_matches(self, rows: Sequence[int]) -> None:
        """Remove the matches at these row indices."""
        bad = [row for row in rows
               if not 0 <= int(row) < len(self.pairs)]
        if bad:
            raise ValueError(f'no match at row {bad[0]}')
        keep = [i for i in range(len(self.pairs))
                if i not in {int(row) for row in rows}]
        self.pairs = [self.pairs[i] for i in keep]
        self.macs = [self.macs[i] for i in keep]

    def rename_source(self, old: str, new: str) -> None:
        """A referenced set or geometry was renamed; the reference
        follows."""
        if self.first == old:
            self.first = new
        if self.second == old:
            self.second = new
        if self.first_geometry == old:
            self.first_geometry = new
        if self.second_geometry == old:
            self.second_geometry = new
