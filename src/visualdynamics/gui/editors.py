"""When a typed number counts as meant.

A Qt spin box reports *every keystroke* by default — `keyboardTracking`
is on unless it is turned off — so typing `50` into an overlap field
emits 5 first and 50 second. That is not merely noisy. Each report is a
real edit here: it lands on the object, the shading moves, the panel
restates the clamped value, and restating it takes the selection away
mid-number, so the second digit has nowhere to go. The field fights the
person typing into it, and 50% overlap cannot be entered at all
(Brandon, 2026-08-27; the same on frame length).

So every spin box in the application commits when the edit is *finished*
— Enter, Tab, clicking elsewhere — or when its own arrows step it. That
is Qt's `keyboardTracking(False)`, and it is a rule about the whole
interface rather than a property of any one field, which is why it is a
call here and not nine scattered ones.

This is not in tension with principle 8, which puts the effort where the
user is waiting: a *drag* is continuous and must stay live, because the
gesture is the value. Typing is not continuous — the half-typed number
is not a number the person means, and treating it as one is the bug.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox

if TYPE_CHECKING:                                    # pragma: no cover
    from PySide6.QtWidgets import QAbstractSpinBox


def commit_on_enter(*boxes: QAbstractSpinBox) -> None:
    """Stop these editors reporting a value the user is still typing.

    Parameters
    ----------
    *boxes : QAbstractSpinBox
        Spin boxes — `QSpinBox`, `QDoubleSpinBox` — whose `valueChanged`
        drives something. Each will report only on a finished edit or a
        step of its own arrows.
    """
    for box in boxes:
        box.setKeyboardTracking(False)


class _Clamping:
    """A spin box that lets a number be typed and then corrects it.

    Qt refuses the keystroke: with a range ending at 1638, typing 2000
    stops after the third digit, because the fourth would make a value
    out of range and the validator calls that invalid. The number never
    appears, nothing says why, and the box simply stops responding
    (Brandon, 2026-08-28).

    Here the typing is allowed and the *value* is corrected when the
    edit finishes — the same clamp-and-restate the panels already use
    for a frame count that will not fit or a resolution that is not
    reachable. What the person typed is a statement of intent; the
    right answer to "2000 Hz" on a record that reaches 1638 is 1638,
    not a box that ignores the last keypress.
    """

    def validate(self, text, position):
        """Accept anything that parses as a number in this box's format.

        Range is deliberately not checked. `valueFromText` is where a
        value out of range is brought back in, which is after the
        person has finished typing rather than during.
        """
        from PySide6.QtGui import QValidator

        stripped = self._number_in(text)
        if stripped == '':
            return (QValidator.State.Intermediate, text, position)
        try:
            float(stripped)
        except ValueError:
            # a lone sign or decimal point on the way to a number
            if stripped in ('-', '+', '.', '-.', '+.'):
                return (QValidator.State.Intermediate, text, position)
            return (QValidator.State.Invalid, text, position)
        return (QValidator.State.Acceptable, text, position)

    def valueFromText(self, text):     
        """The number typed, brought inside the range."""
        stripped = self._number_in(text)
        try:
            value = float(stripped)
        except ValueError:
            return self.value()
        return max(self.minimum(), min(self.maximum(), value))

    def _number_in(self, text):
        """The text with this box's prefix, suffix and separators gone."""
        cleaned = str(text).strip()
        for fixed in (self.prefix(), self.suffix()):
            if fixed and cleaned.endswith(fixed):
                cleaned = cleaned[:-len(fixed)].strip()
            if fixed and cleaned.startswith(fixed):
                cleaned = cleaned[len(fixed):].strip()
        return cleaned.replace(',', '').replace(' ', '').strip()


class SpinBox(_Clamping, QSpinBox):
    """A whole-number box that commits on Enter and clamps what it is
    given. See `_Clamping` and `commit_on_enter`."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setKeyboardTracking(False)

    def valueFromText(self, text):     
        return round(_Clamping.valueFromText(self, text))


class DoubleSpinBox(_Clamping, QDoubleSpinBox):
    """A decimal box that commits on Enter and clamps what it is
    given. See `_Clamping` and `commit_on_enter`."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setKeyboardTracking(False)
