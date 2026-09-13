"""Photos out as the pictures they are.

A `Photos` object holds the file bytes exactly as they arrived — that is
the point of storing them encoded rather than decoded — so writing them
back out is a copy, not a re-encode. A JPEG that goes through this comes
out the same JPEG, byte for byte, and loses no generation.

This writes a *folder*, which is the one place it is not simply the
inverse of reading: a Photos object is ordered and named, and a folder
is neither. The names survive as filenames; the order does not, and is
recovered on the way back in only as far as the file manager's own
sorting takes it. Nothing else about the object is lost — there is
nothing else.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                                    # pragma: no cover
    from ..core.photos import Photos
    from ..units import UnitSystem

#: the extension each stored format is written under
SUFFIX = {'png': '.png', 'jpeg': '.jpg', 'heic': '.heic'}

#: characters a filename cannot carry on some platform or other. A photo
#: may be called anything — 'Fixture 3/4 view' is a fine caption.
UNSAFE = '/\\:*?"<>|'


def handles(obj: Any) -> bool:
    from ..core.photos import Photos

    return isinstance(obj, Photos)


def file_name(name: str, fmt: str, taken: set[str]) -> str:
    """A filename for one photo: its own name, made safe, made unique.

    Two photos may share a name inside the object — nothing stops it —
    and a folder cannot hold two files with one name, so the second gets
    a number rather than silently replacing the first.
    """
    stem = ''.join('-' if c in UNSAFE or ord(c) < 32 else c
                   for c in str(name)).strip(' .') or 'photo'
    suffix = SUFFIX.get(str(fmt).lower(), '.png')
    candidate, n = f'{stem}{suffix}', 1
    while candidate.lower() in taken:
        n += 1
        candidate = f'{stem} ({n}){suffix}'
    taken.add(candidate.lower())
    return candidate


def save(photos: Photos, path: str | os.PathLike,
         unit_system: UnitSystem | None = None, **_kwargs: Any) -> list[str]:
    """Write every photo into the folder `path`, which is made if absent.

    A folder rather than a file, because the object is several pictures
    and a picture format holds one. Returns the paths written, which is
    what a caller staging files for a drag needs.

    `unit_system` is accepted and unused: a photograph has no units.
    """
    folder = str(path)
    # a caller who named a file rather than a folder means the folder it
    # would have sat in — dragging out asks for one, Export As the other
    if os.path.splitext(folder)[1]:
        folder = os.path.splitext(folder)[0]
    os.makedirs(folder, exist_ok=True)

    written, taken = [], set()
    for name, fmt, image in zip(photos.names, photos.formats, photos.images):
        target = os.path.join(folder, file_name(name, fmt, taken))
        with open(target, 'wb') as out:
            out.write(image)
        written.append(target)
    return written
