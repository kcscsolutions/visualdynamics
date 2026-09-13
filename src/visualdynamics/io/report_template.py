"""A report saved on its own, as a template another project can use.

A report is a block model with symbolic bindings — `@basis:Frf`,
`@other:ShapeSet` — so written without its project it is a template:
the same figures and text, bound afresh to whatever project loads it
(Brandon, 2026-09-08: "Is there a way for the user to save a report
template or load a saved report template?"). The file is JSON with one
marker key, the same four fields the project file keeps (`native.py`,
`save_report`), under its own suffix so a folder of them reads as what
it is. A block whose binding does not resolve in the new project is an
unbound card there, to be repointed in the editor's pane, exactly as an
unbound template block already is.

Templates saved into `templates_folder()` — the application's own
folder under the user's application data — are offered by Generate
Report beside the built-in ones, so a house template is one click away
in every new project.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                                    # pragma: no cover
    from ..core.report import Report

SUFFIX = '.vdreport'
MARKER = 'visualdynamics_report_template'


def handles(obj: Any) -> bool:
    from ..core.report import Report

    return isinstance(obj, Report)


def sniff(path: str | os.PathLike) -> bool:
    path = str(path)
    if path.endswith(SUFFIX):
        return True
    if not path.endswith('.json'):
        return False
    try:
        with open(path, encoding='utf-8') as handle:
            return MARKER in handle.read(4096)
    except OSError:
        return False


def save(report: Report, path: str | os.PathLike, unit_system: Any = None,
         **_ignored: Any) -> None:
    """Write the report as a template. `unit_system` is taken for the
    exporter's uniform signature and unused: a template carries no
    values, only what to draw and how to bind it."""
    out = {MARKER: 1, 'title': report.title, 'marking': report.marking,
           'marking_color': report.marking_color,
           'blocks': [dict(block) for block in report.blocks]}
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(out, handle, indent=1)
        handle.write('\n')


def load(path: str | os.PathLike, **_ignored: Any) -> Report:
    from ..core.report import Report

    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or MARKER not in data:
        raise ValueError(f'{path} is not a Visual Dynamics report template')
    return Report(title=str(data.get('title', 'Report')),
                  blocks=data.get('blocks', []),
                  marking=str(data.get('marking', 'UNCLASSIFIED')),
                  marking_color=str(data.get('marking_color', 'ink')))


def templates_folder() -> Path:
    """Where saved templates live: the application's folder under the
    user's application data, as the platform lays it out. Created on
    demand by whoever writes there, not here."""
    override = os.environ.get('VISUALDYNAMICS_TEMPLATES')
    if override:
        return Path(override)
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform.startswith('win'):
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'Visual Dynamics' / 'Report Templates'


def saved_templates() -> list[tuple[str, Path]]:
    """(name, path) for every template in the folder, by name."""
    folder = templates_folder()
    if not folder.is_dir():
        return []
    return sorted((path.name[:-len(SUFFIX)], path)
                  for path in folder.iterdir()
                  if path.is_file() and path.name.endswith(SUFFIX))
