"""The scripted workflow example stays honest.

examples/modal_workflow.py is the promise that everything the GUI
does — import, process, fit, correlate, match, plot, save, report —
runs from plain Python. This runs it in a clean interpreter and holds
it to that promise: every output real, and the app itself
(`visualdynamics.gui`) never imported. Qt *is* imported, because rendering a
plot is Qt's job whether a window opens or not; what the promise
means is that no application shell is needed.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_scripted_workflow_needs_no_gui(tmp_path):
    probe = (
        'import os, runpy, sys\n'
        'os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")\n'
        f'sys.argv = ["modal_workflow.py", {str(tmp_path)!r}]\n'
        'runpy.run_path("examples/modal_workflow.py", '
        'run_name="__main__")\n'
        'print("app imported:", "visualdynamics.gui" in sys.modules)\n'
    )
    result = subprocess.run([sys.executable, '-c', probe], cwd=ROOT,
                            capture_output=True, text=True, timeout=900,
                            check=False)
    assert result.returncode == 0, result.stderr[-2000:]
    assert 'app imported: False' in result.stdout, (
        'the workflow reached for the application shell')
    assert (tmp_path / 'modal.vdyn').exists()
    for figure in ('frfs.png', 'cmif.png', 'automac.png', 'crossmac.png',
                   'coherence.png', 'excitation.png', 'mode1.png'):
        assert (tmp_path / figure).stat().st_size > 1000, figure
    html = (tmp_path / 'modal_report.html').read_text(encoding='utf-8')
    assert 'Matched modes' in html, 'the matched table rendered'
    assert 'flat' in html, 'the overlay animation rendered'
    # and the saved project is the GUI's own format, links and all
    import visualdynamics

    back = visualdynamics.Project.open(tmp_path / 'modal.vdyn')
    assert back.project_type == 'Modal Test'
    assert back.basis, 'the Basis group rode the file'
    assert 'Matched Modes' in back
