"""Screenshot watermarking and destination helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap, QRegion


def screenshot_directory() -> Path:
    """Return the user-visible folder used for finished screenshots."""
    pictures = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.PicturesLocation
    )
    base = Path(pictures) if pictures else Path.home() / "Pictures"
    return base / "Macbeth Screenshots"


def next_screenshot_path(directory: Path, now: datetime | None = None) -> Path:
    """Create a readable, collision-free PNG destination path."""
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    candidate = directory / f"Macbeth_{timestamp}.png"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"Macbeth_{timestamp}_{suffix}.png"
        suffix += 1
    return candidate


def add_sitting_watermark(screenshot: QImage, sitting_dog: QPixmap) -> QImage:
    """Place a small, translucent sitting dog in the bottom-right corner."""
    result = screenshot.convertToFormat(QImage.Format.Format_ARGB32)
    if result.isNull() or sitting_dog.isNull():
        return result

    opaque_bounds = QRegion(sitting_dog.mask()).boundingRect()
    dog = sitting_dog.copy(opaque_bounds) if not opaque_bounds.isEmpty() else sitting_dog

    shortest_side = min(result.width(), result.height())
    target_height = max(48, min(220, round(shortest_side * 0.16)))
    dog = dog.scaledToHeight(
        target_height,
        Qt.TransformationMode.FastTransformation,
    )
    margin = max(14, round(shortest_side * 0.018))
    x = max(0, result.width() - dog.width() - margin)
    y = max(0, result.height() - dog.height() - margin)

    painter = QPainter(result)
    painter.setOpacity(0.78)
    painter.drawPixmap(x, y, dog)
    painter.end()
    return result

