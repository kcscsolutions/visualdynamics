"""Is there a newer version than this one?

A check, not an updater. It asks one URL for one small JSON file, and
the answer goes in a status line: *0.1.0 is available*. Nothing is
downloaded, nothing is replaced, nothing runs with privileges.

That is a deliberate stopping point. A real auto-updater has to verify
what it downloaded before executing it, which means signing keys and a
threat model — an unverified one is a remote code execution feature
with a friendly name. Sparkle (macOS) and WinSparkle do it properly and
can be adopted later; until there is a signing identity to verify
against, telling the user beats pretending.

The manifest lives on `visualdynamics.org`, a static host with no
server to run — the release workflow writes it from each published
release and deploys it with the site (`web/public/latest.json` is the
holding page's copy). Its shape:

    {"version": "0.1.0", "url": "https://…/releases", "notes": "…"}
"""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from . import __version__

MANIFEST = 'https://visualdynamics.org/latest.json'
TIMEOUT = 4.0


def parse_version(text: str) -> tuple[int, ...]:
    """'0.10.2' -> (0, 10, 2, 1, 0), for comparing rather than for showing.

    Numeric, so 0.10 sorts above 0.9 — a string compare puts them the
    other way round and would offer a downgrade as an upgrade. Anything
    unparseable becomes zero rather than raising: a malformed manifest
    should mean *no update offered*, never a traceback in front of
    somebody who only opened the application.

    A pre-release sorts *below* its release: '0.1.0a1' is (0, 1, 0, 0,
    1) and '0.1.0' is (0, 1, 0, 3, 0), so the first non-alpha 0.1.0 is
    offered to an alpha as the upgrade it is (2026-09-11). The stage is
    a for alpha, b for beta, rc for a candidate — Python's own
    spelling, and the one the version string carries — and a release
    is stage 3, above them all.
    """
    text = str(text).strip().lstrip('v')
    release, stage, number = text, 3, 0
    for rank, tag in enumerate(('a', 'b', 'rc')):
        head, found, tail = text.partition(tag)
        if found and head and head[-1].isdigit() and (tail == '' or tail.isdigit()):
            release, stage, number = head, rank, int(tail or 0)
            break
    parts: list[int] = []
    for piece in release.split('.'):
        digits = ''.join(c for c in piece if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return (*parts, stage, number)


def newer(available: str, running: str = __version__) -> bool:
    """Is `available` a later version than what is running?"""
    return parse_version(available) > parse_version(running)


def fetch(url: str = MANIFEST, timeout: float = TIMEOUT) -> dict[str, Any] | None:
    """The manifest as published, or None when it cannot be had.

    `check` folds "nothing newer" and "could not ask" into one answer,
    which is right for a check that runs unasked. Asked for from a
    menu, the two deserve different words — up to date is not the same
    news as offline — so the fetch stands on its own.
    """
    try:
        request = Request(url, headers={
            'User-Agent': f'VisualDynamics/{__version__}'})
        with urlopen(request, timeout=timeout) as response:
            manifest = json.loads(response.read(64_000).decode('utf-8'))
    except Exception:      # noqa: BLE001 — see the docstring: every
        return None        # failure here means 'no manifest', never a
                           # traceback in front of somebody who only
                           # opened the application
    return manifest if isinstance(manifest, dict) else None


def check(url: str = MANIFEST, timeout: float = TIMEOUT) -> dict[str, Any] | None:
    """The manifest when it offers something newer, else None.

    Every failure is None: no network, a captive portal, a 404, a
    truncated file, a version that does not parse. An update check is
    the least important thing the application does and must never be
    the reason it is slow to start or noisy on launch — which is why
    this takes a timeout and why the caller runs it off the main
    thread.
    """
    manifest = fetch(url, timeout)
    if manifest is None:
        return None
    version = str(manifest.get('version', ''))
    return manifest if version and newer(version) else None
