"""What the application remembers between launches: today, the
appearance.

One `QSettings` under one name, so a preference set on one launch is
read on the next; the tests point the store at a temporary folder
through `QSettings.setPath`, so nothing a test chooses reaches the
user's own file.

The appearance a window wears is decided in this order, and the order
is the point: an explicit statement for this launch
(`VISUALDYNAMICS_THEME`, which `--theme` sets) beats the remembered
choice, and the remembered choice beats what the platform reports —
`'system'` means follow the platform, which is the default and what
`theme.system_scheme` answers.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QSettings

from ..theme import OVERRIDE, THEMES, system_scheme

#: the remembered choices, in menu order
APPEARANCES = ('system', 'light', 'dark')
KEY = 'appearance'


def settings() -> QSettings:
    """The application's own store."""
    return QSettings('visualdynamics', 'Visual Dynamics')


def remembered_appearance() -> str:
    """'system', 'light' or 'dark' — 'system' when nothing was chosen
    or the stored word is not one of ours."""
    said = str(settings().value(KEY, 'system')).strip().lower()
    return said if said in APPEARANCES else 'system'


def remember_appearance(choice: str) -> None:
    """Store the choice; 'system' clears it rather than storing a word
    that means "nothing chosen"."""
    if choice not in APPEARANCES:
        raise ValueError(f'appearance is one of {APPEARANCES}, not {choice!r}')
    store = settings()
    if choice == 'system':
        store.remove(KEY)
    else:
        store.setValue(KEY, choice)
    store.sync()


def chosen_scheme() -> str:
    """The theme to wear now: this launch's statement, else the
    remembered choice, else the platform's."""
    said = os.environ.get(OVERRIDE, '').strip().lower()
    if said in THEMES:
        return said
    remembered = remembered_appearance()
    if remembered in THEMES:
        return remembered
    return system_scheme()
