"""Generate multi-resolution Windows .ico and high-res .png for SENTRON.

Uses PySide6 offscreen vector rendering and Pillow to produce:
- packaging/assets/sentron.ico (containing 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256)
- packaging/assets/sentron.png (256x256)
Offline, zero untrusted external assets.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

# Ensure headless offscreen platform for Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)


def render_shield_image(size: int) -> Image.Image:
    """Render the circular golden shield vector icon at the specified pixel size."""
    qimg = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    qimg.fill(Qt.transparent)

    painter = QPainter(qimg)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    w = float(size)
    h = float(size)
    d = min(w, h)
    cx = w / 2.0
    cy = h / 2.0
    r = (d - max(2.0, d * 0.05)) / 2.0

    # 1. Circular dark background with crisp golden border
    pen = QPen(QColor("#E2B83B"), max(1.5, d * 0.04))
    brush = QBrush(QColor("#171717"))
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(QPointF(cx, cy), r, r)

    # 2. Golden-yellow shield outer silhouette
    sw = d * 0.44
    sh = d * 0.52
    top = cy - sh / 2.0
    bottom = cy + sh / 2.0
    left = cx - sw / 2.0
    right = cx + sw / 2.0

    path = QPainterPath()
    path.moveTo(cx, top)
    path.lineTo(right, top + sh * 0.08)
    path.lineTo(right, cy)
    path.cubicTo(right, cy + sh * 0.25, cx + sw * 0.2, bottom - sh * 0.08, cx, bottom)
    path.cubicTo(cx - sw * 0.2, bottom - sh * 0.08, left, cy + sh * 0.25, left, cy)
    path.lineTo(left, top + sh * 0.08)
    path.closeSubpath()

    shield_color = QColor("#E2B83B")
    painter.setPen(QPen(shield_color, max(1.0, d * 0.02)))
    painter.setBrush(QBrush(shield_color))
    painter.drawPath(path)

    # 3. Inner dark core for contrast and security shield depth
    in_w = sw * 0.60
    in_h = sh * 0.60
    in_top = cy - in_h / 2.0 + 1.0
    in_bottom = cy + in_h / 2.0
    in_left = cx - in_w / 2.0
    in_right = cx + in_w / 2.0

    inner_path = QPainterPath()
    inner_path.moveTo(cx, in_top)
    inner_path.lineTo(in_right, in_top + in_h * 0.08)
    inner_path.lineTo(in_right, cy)
    inner_path.cubicTo(in_right, cy + in_h * 0.22, cx + in_w * 0.2, in_bottom - in_h * 0.08, cx, in_bottom)
    inner_path.cubicTo(cx - in_w * 0.2, in_bottom - in_h * 0.08, in_left, cy + in_h * 0.22, in_left, cy)
    inner_path.lineTo(in_left, in_top + in_h * 0.08)
    inner_path.closeSubpath()

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#171717")))
    painter.drawPath(inner_path)

    painter.end()

    # Convert QImage to PIL Image via QBuffer
    from PySide6.QtCore import QBuffer, QByteArray
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    qimg.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(ba.data()))


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    output_dir = Path(__file__).resolve().parent / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = {}
    for s in sizes:
        images[s] = render_shield_image(s)

    # Save master PNG
    png_path = output_dir / "sentron.png"
    images[256].save(png_path, "PNG")
    print(f"Saved {png_path}")

    # Save multi-resolution ICO
    ico_path = output_dir / "sentron.ico"
    # PIL saves all resolutions into a single ICO file
    images[256].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=[images[s] for s in [128, 64, 48, 32, 24, 16]],
    )
    print(f"Saved {ico_path} with resolutions: {sizes}")


if __name__ == "__main__":
    main()
