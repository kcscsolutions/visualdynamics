"""File → Check for Updates: the answer in words, never an action.

The window asks `update.fetch` off the main thread and says one of
three things: a newer version is available (with the page to open),
this one is up to date, or visualdynamics.org could not be reached —
offline is not the same news as current. Nothing is downloaded and
nothing runs; `update.py` explains why.
"""

from __future__ import annotations

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from visualdynamics import __version__, update


def _answer(window, pump, monkeypatch, manifest):
    monkeypatch.setattr(update, 'fetch', lambda *a, **k: manifest)
    window.check_for_updates()
    for _ in range(50):                    # the thread's answer arrives
        QTest.qWait(20)
        if 'Checking' not in window.statusBar().currentMessage():
            break
    pump(3)
    return window.statusBar().currentMessage()


def test_the_menu_offers_it(window):
    labels = [a.text() for a in window.menuBar().actions()
              for a in a.menu().actions()]
    assert 'Check for &Updates...' in labels


def test_offline_is_said_as_offline(window, pump, monkeypatch):
    said = _answer(window, pump, monkeypatch, None)
    assert 'Could not reach' in said
    assert 'up to date' not in said, 'offline must never read as current'


def test_the_same_version_is_up_to_date(window, pump, monkeypatch):
    said = _answer(window, pump, monkeypatch, {'version': __version__})
    assert 'up to date' in said
    assert __version__ in said


def test_a_newer_version_is_offered_as_a_page_to_open(window, pump,
                                                       monkeypatch):
    opened = []
    from PySide6.QtGui import QDesktopServices
    monkeypatch.setattr(QDesktopServices, 'openUrl',
                        staticmethod(lambda url: opened.append(url.toString())))
    said = _answer(window, pump, monkeypatch, {
        'version': '99.0.0', 'url': 'https://visualdynamics.org/get',
        'notes': 'Everything works now.'})
    assert '99.0.0 is available' in said
    box = window.findChild(QMessageBox)
    assert box is not None and box.isVisible(), 'the offer is a box to act on'
    assert '99.0.0' in box.text() and __version__ in box.text()
    assert box.informativeText() == 'Everything works now.'
    opener = next(b for b in box.buttons() if 'Open' in b.text())
    opener.click()
    pump(3)
    assert opened == ['https://visualdynamics.org/get'], (
        'the page opens in the browser; nothing is downloaded here')
