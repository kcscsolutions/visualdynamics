"""Dividers on a plot's bar, and what they are telling the reader.

A control bar here holds two kinds of thing, and they behave
differently enough that running them together is a small lie about how
the interface works:

- **Choices.** Curves or Map. Averaging, Filter, Kurtosis or Shocks.
  Exactly one is in force, and picking one drops the last — they are a
  set, and the reader needs to know which set.
- **Settings.** The 2-D/3-D toggle, which quantity stands on the stage,
  which page of channels, Drive points, CMIF. Each is independent of
  the rest and orthogonal to whichever choice is in force: 3-D is not a
  fifth way of reading a record, it is how any of them is drawn
  (Brandon, 2026-08-27).

Undivided, a row of icons says nothing about which is which, and a
person has to click one to find out whether it turns another off. A
divider says it before they click.

Two functions, because the bars are built once and hidden down to what
the current selection can use: `fence` puts the dividers in at build
time, and `tidy` decides at show time which of them still divide
anything. Neither is a per-bar decision — a bar that wanted its own
rule would be a bar that reads differently from the others.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def fence(toolbar: Any, runs: Iterable[Sequence[Any]]) -> None:
    """Put a divider on each side of every run of actions.

    Parameters
    ----------
    toolbar : QToolBar
        The bar to fence. Its actions are reordered only in the sense
        that separators are inserted between them; nothing moves past
        anything else.
    runs : iterable of sequence of QAction
        Each run is a group that belongs together — the actions of a
        `QActionGroup`, or a lone setting that should stand apart. A
        run whose actions are not adjacent on the bar is fenced from
        its first to its last, so keep a group's actions together when
        adding them.

    Notes
    -----
    Adding a divider is cheap and safe: `tidy` hides the ones that turn
    out to divide nothing, so a fence around a group that the current
    selection hides entirely does not leave a stray line behind. That
    is what makes it reasonable to fence *every* group rather than
    picking the ones that seemed to need it.
    """
    for run in runs:
        actions = [action for action in run if action is not None]
        if not actions:
            continue
        current = toolbar.actions()
        try:
            first = min(current.index(action) for action in actions)
            last = max(current.index(action) for action in actions)
        except ValueError:            # an action that is not on this bar
            continue
        toolbar.insertSeparator(current[first])
        if last + 1 < len(current):
            toolbar.insertSeparator(current[last + 1])
        else:
            toolbar.addSeparator()


def tidy(toolbar: Any) -> None:
    """Show only the dividers that still divide something.

    The bar is built with every control on it and then hidden down to
    what the current selection can use, so which groups survive differs
    every time. A divider with nothing on one side is a fence around an
    empty field: it reads as a group gone missing rather than as one
    that does not apply, which is the opposite of what it is there for.

    The rule: keep a separator when a visible control stands somewhere
    before it and somewhere after it, and none has already been kept
    since the last visible control. That drops leading and trailing
    dividers, and **collapses a run of adjacent ones to a single
    divider** rather than to none — which is the case that matters,
    because two groups fenced side by side put two separators together
    and dropping both would run the groups into each other. Found by
    looking at the bar: Curves/Map ran straight into the 3-D toggle.
    """
    actions = toolbar.actions()
    # is there a visible control still to come, at each position?
    ahead = [False] * (len(actions) + 1)
    for index in range(len(actions) - 1, -1, -1):
        action = actions[index]
        ahead[index] = ahead[index + 1] or (
            not action.isSeparator() and action.isVisible())

    pending = False          # a visible control since the last divider kept
    for index, action in enumerate(actions):
        if action.isSeparator():
            keep = pending and ahead[index + 1]
            action.setVisible(keep)
            if keep:
                pending = False
        elif action.isVisible():
            pending = True


def shows_anything(toolbar: Any) -> bool:
    """Whether the bar has a visible control on it — dividers aside.

    A separator is visible whether or not anything is around it, so a
    bar of nothing but dividers passes a plain `any(isVisible)` and
    stays up. `tidy` first, then this.
    """
    return any(action.isVisible() for action in toolbar.actions()
               if not action.isSeparator())
