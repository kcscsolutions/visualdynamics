#!/usr/bin/env python3
"""Draw the .dmg window's background: the drag-to-install arrow.

    packaging/dmg_background.py <out.png>

Generated, not drawn by hand, like the site's mark and the app icon —
so the artwork cannot rot in a corner of the repository. The image is
rendered at 2x with its DPI stamped, which is how Finder shows it
sharp on retina at the window's 660 x 420 points; the icon spots the
arrow points between are the same coordinates `build_macos.sh` gives
Finder for the two icons.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

#: the window in points, and where the two icons sit in it
WINDOW = (660, 420)
APP_SPOT = (165, 195)
APPLICATIONS_SPOT = (495, 195)


def draw(path: str) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    scale = 2
    image = QImage(WINDOW[0] * scale, WINDOW[1] * scale,
                   QImage.Format.Format_RGB32)
    dots_per_meter = round(72 * scale / 0.0254)
    image.setDotsPerMeterX(dots_per_meter)
    image.setDotsPerMeterY(dots_per_meter)
    image.fill(QColor('#f5f5f7'))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(scale, scale)
    # the arrow crosses the gap between the two icon spots, at their
    # own height, with air on both sides so it never touches a label
    y = APP_SPOT[1]
    start, end = APP_SPOT[0] + 90, APPLICATIONS_SPOT[0] - 90
    head = 26
    pen = QPen(QColor('#b9b9c0'), 14, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(start, y, end - head + 4, y)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#b9b9c0'))
    painter.drawPolygon(QPolygonF([
        QPointF(end, y),
        QPointF(end - head, y - head * 0.7),
        QPointF(end - head, y + head * 0.7)]))
    painter.end()
    image.save(path, 'PNG')


if __name__ == '__main__':
    draw(sys.argv[1])
