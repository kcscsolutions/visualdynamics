"""Build `visualdynamics.app` — a Mac icon that launches the GUI.

    python tools/make_app.py [destination]

Not a bundled application. The dependencies are two gigabytes of Qt and
VTK, and freezing them would take a quarter of an hour to produce
something that goes stale the moment the source changes. This is a
launcher: a real `.app` with a real icon, which Finder, Spotlight and
the Dock treat as an application, and which runs the checkout's own
interpreter. Edit the source and the next launch has the edit.

The consequence is that it points at *this* checkout by absolute path.
Move the repository and the icon stops working — rerun this and it
points at the new place.

The icon is drawn here rather than shipped as a file, the same way the
tree's icons are: one deflected mode on a dark tile, which is the app's
own scene in miniature.
"""

from __future__ import annotations

import os
import pathlib
import plistlib
import shutil
import subprocess
import sys

from visualdynamics import __version__

ROOT = pathlib.Path(__file__).resolve().parent.parent
#: what a person sees — the bundle, the Dock, the menu bar
NAME = 'Visual Dynamics'

#: what the filesystem sees. The executable inside a bundle and the
#: files beside it are named without a space, because a launcher whose
#: own name needs quoting in every shell that touches it is a small
#: recurring tax for no gain. The two differ on purpose: one is read,
#: the other is typed.
SLUG = 'visualdynamics'
BUNDLE_ID = 'com.bzwink.vdyn'

#: the sizes a macOS iconset wants, and the name each goes under. Finder
#: picks by size, so a missing one is a blurry icon at that size and
#: nowhere else.
ICONSET = [
    (16, 'icon_16x16.png'), (32, 'icon_16x16@2x.png'),
    (32, 'icon_32x32.png'), (64, 'icon_32x32@2x.png'),
    (128, 'icon_128x128.png'), (256, 'icon_128x128@2x.png'),
    (256, 'icon_256x256.png'), (512, 'icon_256x256@2x.png'),
    (512, 'icon_512x512.png'), (1024, 'icon_512x512@2x.png'),
]


def draw_icon(size):
    """The app's own icon at `size` pixels, as PNG bytes.

    The drawing lives in the package (`gui.icons.draw_app_icon`) and is
    the one the running window wears, so the Dock tile and the window's
    own icon cannot drift apart.
    """
    from PySide6.QtCore import QBuffer, QByteArray

    from visualdynamics.gui.icons import draw_app_icon

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    draw_app_icon(size).save(buffer, 'PNG')
    return bytes(data.data())


def build_icns(destination):
    """The .icns, via `iconutil` — macOS's own converter, so the result
    is what Finder expects rather than what a library guessed."""
    iconset = destination.parent / f'{SLUG}.iconset'
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    for size, name in ICONSET:
        (iconset / name).write_bytes(draw_icon(size))
    subprocess.run(['iconutil', '--convert', 'icns', '--output',
                    str(destination), str(iconset)], check=True)
    shutil.rmtree(iconset)


#: what Finder runs.
#:
#: `exec` so the app *is* the interpreter rather than a shell waiting on
#: one — otherwise Activity Monitor lists two processes and neither is
#: the app. `-a visualdynamics` sets the name that replaces it, which is why this
#: is bash and not sh: without it every list on the machine that names a
#: running process — Force Quit, Activity Monitor, `ps` — calls this
#: 'python', and so does the menu bar.
LAUNCHER = '''#!/bin/bash
# Written by tools/make_app.py. Points at the checkout it was built from;
# move the repository and rebuild.
exec -a visualdynamics "{python}" -m visualdynamics "$@"
'''


def build(destination):
    """Write the bundle, replacing any bundle already there."""
    app = pathlib.Path(destination).expanduser().resolve() / f'{NAME}.app'
    if app.exists():
        shutil.rmtree(app)
    macos = app / 'Contents' / 'MacOS'
    resources = app / 'Contents' / 'Resources'
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    python = ROOT / '.venv' / 'bin' / 'python'
    if not python.exists():
        python = pathlib.Path(sys.executable)
    launcher = macos / SLUG
    launcher.write_text(LAUNCHER.format(python=python))
    launcher.chmod(0o755)

    build_icns(resources / f'{SLUG}.icns')

    (app / 'Contents' / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleName': NAME,
        'CFBundleDisplayName': 'Visual Dynamics',
        'CFBundleIdentifier': BUNDLE_ID,
        'CFBundleExecutable': SLUG,
        'CFBundleIconFile': f'{SLUG}.icns',
        'CFBundlePackageType': 'APPL',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleShortVersionString': __version__,
        'CFBundleVersion': __version__,
        # Retina, and a normal windowed app rather than a menu-bar one
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
        'NSPrincipalClass': 'NSApplication',
    }))
    # Finder caches an app's icon by path; a bundle rewritten in place
    # keeps showing the old one until its modification time moves
    os.utime(app, None)
    return app


if __name__ == '__main__':
    where = sys.argv[1] if len(sys.argv) > 1 else '~/Applications'
    target = pathlib.Path(where).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    built = build(target)
    print(f'wrote {built}')
    print('Double-click it, or drag it to the Dock. It runs '
          f'{ROOT / ".venv" / "bin" / "python"} -m visualdynamics,')
    print('so an edit to the source is live on the next launch.')
