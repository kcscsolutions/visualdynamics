"""Photos: pictures of the test, riding in the project.

A Photos object is an ordered set of named images — the setup and
instrumentation photos a test report leans on. It keeps the file bytes
verbatim (PNG or JPEG), so nothing is re-encoded and what went in is
exactly what comes out, in the project file and in the report.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

FORMATS = {'.png': 'png', '.jpg': 'jpeg', '.jpeg': 'jpeg'}


class Photos:
    """Named images, in the order they arrived.

    Setup photographs belong with the data they document — where the
    accelerometers went, how the article was hung — so they are a project
    object like any other and ride the `.vdyn` file. The bytes are kept
    encoded as they arrived rather than decoded into arrays: a report
    embeds them, and re-encoding a JPEG to store it would lose a
    generation for nothing.

    Attributes:
        names: What each photo is called, which is what a report figure
            is captioned with.
        formats: The encoding of each — `'png'`, `'jpeg'`, `'heic'`.
        images: The encoded bytes, one per photo.
    """

    def __init__(self, names: Sequence[str] | None = None,
                 formats: Sequence[str] | None = None,
                 images: Sequence[bytes] | None = None) -> None:
        self.names: list[str] = [str(name) for name in (names or [])]
        self.formats: list[str] = [str(fmt) for fmt in (formats or [])]
        self.images: list[bytes] = [bytes(image) for image in (images or [])]
        if not (len(self.names) == len(self.formats) == len(self.images)):
            raise ValueError('names, formats and images must match up')

    def __repr__(self) -> str:
        count = self.num_photos
        return f'Photos({count} photo{"s" * (count != 1)})'

    @property
    def num_photos(self) -> int:
        return len(self.names)

    def rename(self, index: int, name: str) -> None:
        """Give the photo at `index` a new name; names stay unique."""
        name = str(name).strip()
        if not name:
            raise ValueError('a photo needs a name')
        if name in self.names and self.names.index(name) != index:
            raise ValueError(f"there is already a photo named '{name}'")
        self.names[index] = name

    def delete_photos(self, picks: Sequence[int]) -> None:
        """Remove the photos at `picks` (indices)."""
        doomed = set(picks)
        keep = [i for i in range(self.num_photos) if i not in doomed]
        self.names = [self.names[i] for i in keep]
        self.formats = [self.formats[i] for i in keep]
        self.images = [self.images[i] for i in keep]

    def add_file(self, path: str | os.PathLike) -> str:
        """Add an image file; the name is the file's own stem, deduped.

        Returns the name the photo landed under.
        """
        extension = os.path.splitext(path)[1].lower()
        if extension not in FORMATS:
            raise ValueError(
                f'Not a photo (want png or jpeg): {os.path.basename(path)}')
        name = os.path.splitext(os.path.basename(path))[0]
        base, n = name, 1
        while name in self.names:
            n += 1
            name = f'{base} ({n})'
        with open(path, 'rb') as source:
            self.images.append(source.read())
        self.names.append(name)
        self.formats.append(FORMATS[extension])
        return name

    def plot(self, picks: Sequence[int] | None = None, **kwargs: Any) -> Any:
        """Show these photos, as the app shows them."""
        from ..plot import plot_photos
        return plot_photos(self, picks, **kwargs)
