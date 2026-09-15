"""File → Appearance: light, dark, or the platform's, remembered.

A friend of Brandon's on a Linux desktop Qt could not read got a light
window and no way to change it (2026-09-14). The menu is the user's
toggle; the choice is stored and worn on the next launch; System means
follow the platform again, which is the default. This launch's own
statement (`--theme`, the environment) beats the remembered choice.
"""

from __future__ import annotations

import pytest

from visualdynamics.gui import preferences
from visualdynamics.theme import OVERRIDE


@pytest.fixture(autouse=True)
def fresh_store(monkeypatch):
    monkeypatch.delenv(OVERRIDE, raising=False)
    preferences.remember_appearance('system')
    yield
    preferences.remember_appearance('system')


def _appearance_actions(window):
    file_menu = next(m for m in window.menuBar().findChildren(type(window.menuBar().actions()[0].menu()))
                     if m.title() == '&File')
    submenu = next(a.menu() for a in file_menu.actions()
                   if a.menu() is not None and a.text() == '&Appearance')
    return {a.text(): a for a in submenu.actions()}


def test_the_menu_offers_three_exclusive_choices_with_system_checked(window):
    actions = _appearance_actions(window)
    assert list(actions) == ['&System', '&Light', '&Dark']
    assert all(a.isCheckable() for a in actions.values())
    assert actions['&System'].isChecked()
    assert actions['&Light'].actionGroup() is actions['&Dark'].actionGroup()
    assert actions['&Light'].actionGroup().isExclusive()


def test_a_choice_is_worn_now_and_remembered_for_the_next_window(
        window, pump, window_factory):
    actions = _appearance_actions(window)
    actions['&Dark'].trigger()
    pump()
    assert window.theme_name == 'dark'
    assert actions['&Dark'].isChecked() and not actions['&System'].isChecked()
    assert preferences.remembered_appearance() == 'dark'
    # the next launch: a fresh window reads the store
    later = window_factory()
    assert later.theme_name == 'dark'
    assert _appearance_actions(later)['&Dark'].isChecked()
    actions['&Light'].trigger()
    pump()
    assert window.theme_name == 'light'
    assert preferences.remembered_appearance() == 'light'


def test_system_follows_the_platform_again(window, pump, monkeypatch):
    actions = _appearance_actions(window)
    actions['&Dark'].trigger()
    pump()
    monkeypatch.setattr(preferences, 'system_scheme', lambda: 'light')
    actions['&System'].trigger()
    pump()
    assert window.theme_name == 'light'
    assert preferences.remembered_appearance() == 'system'
    # and a platform switch is followed only while System is chosen
    monkeypatch.setattr(preferences, 'system_scheme', lambda: 'dark')
    window._scheme_changed(None)
    assert window.theme_name == 'dark'
    actions['&Light'].trigger()
    pump()
    window._scheme_changed(None)
    assert window.theme_name == 'light', 'a chosen appearance ignores the platform'


def test_this_launchs_statement_beats_the_remembered_choice(monkeypatch):
    preferences.remember_appearance('dark')
    assert preferences.chosen_scheme() == 'dark'
    monkeypatch.setenv(OVERRIDE, 'light')
    assert preferences.chosen_scheme() == 'light'


def test_the_store_refuses_a_word_that_is_not_an_appearance():
    with pytest.raises(ValueError):
        preferences.remember_appearance('sepia')
