"""About Visual Dynamics: the version, readable without the network.

Brandon, 2026-09-12: the version showed only on the alpha notice, in
the update check's status line and in the installer's file name. The
About box says it, and what the release is, on demand; macOS puts the
action in the application menu through its role.
"""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from visualdynamics import __version__


def test_the_menu_offers_about_with_the_about_role(window):
    actions = [a for menu in window.menuBar().actions()
               for a in menu.menu().actions()]
    about = next(a for a in actions if a.text() == '&About Visual Dynamics...')
    assert about.menuRole() == QAction.MenuRole.AboutRole, \
        'macOS moves it into the application menu'


def test_the_box_says_the_version_and_what_it_is(window, pump):
    window.about()
    pump()
    box = window.about_box
    assert isinstance(box, QMessageBox) and box.isVisible()
    assert __version__ in box.text(), 'the version, first'
    assert 'alpha release' in box.informativeText()
    assert 'contact@visualdynamics.org' in box.informativeText()
    assert 'LICENSE' in box.text()
    box.close()
