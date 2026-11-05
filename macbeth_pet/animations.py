"""Sprite-sheet loading, fallback artwork, and animation definitions."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QTransform

from .behavior import PetState

LOGGER = logging.getLogger(__name__)

# Cell numbering is left-to-right, top-to-bottom:
#   0 1 2
#   3 4 5
#   6 7 8
# Change only this mapping if a replacement sheet uses different poses.
ANIMATION_FRAMES: dict[PetState, tuple[int, ...]] = {
    PetState.IDLE: (5,),
    PetState.SIT: (4,),
    PetState.WALK: (5, 0),
    PetState.RUN: (0, 8),
    PetState.WAVE: (7, 4, 7, 4),
    PetState.REST: (3,),
    PetState.SLEEP: (3,),
    PetState.POSE: (0,),
}

SIT_FRAME_CHOICES = (1, 2, 4, 6)

# The supplied sheet mixes left- and right-facing artwork. Normalizing this
# before applying the requested direction prevents walk/run frames from
# appearing to spin back and forth.
FRAMES_DRAWN_FACING_LEFT = frozenset({0, 3, 6})

FRAME_INTERVAL_MS: dict[PetState, int] = {
    PetState.IDLE: 650,
    PetState.SIT: 900,
    PetState.WALK: 220,
    PetState.RUN: 115,
    PetState.WAVE: 260,
    PetState.REST: 800,
    PetState.SLEEP: 950,
    PetState.POSE: 900,
}


@dataclass(frozen=True)
class SpriteSet:
    frames: tuple[QPixmap, ...]
    source: Path | None
    is_fallback: bool

    def frame(self, index: int, facing_left: bool = False) -> QPixmap:
        normalized_index = index % len(self.frames)
        pixmap = self.frames[normalized_index]
        source_faces_left = normalized_index in FRAMES_DRAWN_FACING_LEFT
        if source_faces_left == facing_left:
            return pixmap
        return pixmap.transformed(
            QTransform().scale(-1.0, 1.0),
            Qt.TransformationMode.FastTransformation,
        )


def load_sprite_set(path: Path | None, display_size: int) -> SpriteSet:
    """Load and split a 3×3 sheet, or create a friendly built-in fallback."""
    if path is not None and path.is_file():
        image = QImage(str(path))
        if not image.isNull() and image.width() >= 3 and image.height() >= 3:
            frames = []
            for row in range(3):
                for column in range(3):
                    left = column * image.width() // 3
                    right = (column + 1) * image.width() // 3
                    top = row * image.height() // 3
                    bottom = (row + 1) * image.height() // 3
                    cell = image.copy(
                        left,
                        top,
                        right - left,
                        bottom - top,
                    )
                    frames.append(_scaled_pixmap(cell, display_size))
            LOGGER.info("Loaded 3×3 sprite sheet from %s", path)
            return SpriteSet(tuple(frames), path, False)
        LOGGER.warning("Could not decode sprite sheet %s; using fallback art.", path)
    elif path is not None:
        LOGGER.warning("Sprite sheet %s was not found; using fallback art.", path)
    else:
        LOGGER.warning("No sprite sheet was found; using fallback art.")

    return SpriteSet(_create_fallback_frames(display_size), None, True)


def _scaled_pixmap(image: QImage, display_size: int) -> QPixmap:
    scaled = QPixmap.fromImage(image).scaled(
        display_size,
        display_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    canvas = QPixmap(display_size, display_size)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap(
        (display_size - scaled.width()) // 2,
        display_size - scaled.height(),
        scaled,
    )
    painter.end()
    return canvas


def _create_fallback_frames(display_size: int) -> tuple[QPixmap, ...]:
    """Draw nine small terrier-like poses without external assets."""
    poses = (
        (0.0, 0.0, False, False),
        (0.0, -2.0, False, False),
        (0.0, 5.0, True, False),
        (-3.0, 0.0, False, False),
        (3.0, 0.0, False, False),
        (0.0, -4.0, False, False),
        (0.0, 2.0, True, True),
        (0.0, 12.0, False, False),
        (2.0, 14.0, False, False),
    )
    return tuple(_draw_fallback_frame(display_size, *pose) for pose in poses)


def _draw_fallback_frame(
    size: int,
    step: float,
    lift: float,
    sitting: bool,
    waving: bool,
) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = size / 160.0
    painter.scale(scale, scale)
    painter.translate(0.0, lift)

    fur = QColor("#171719")
    shadow = QColor(0, 0, 0, 45)
    highlight = QColor("#333338")
    eye = QColor("#d99a42")
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shadow)
    painter.drawEllipse(QRectF(28, 137, 110, 10))

    # Body, chest and distinctive Scottish Terrier head.
    painter.setBrush(fur)
    body_y = 82 if not sitting else 88
    painter.drawRoundedRect(QRectF(34, body_y, 78, 45), 18, 18)
    painter.drawEllipse(QRectF(94, 54, 43, 51))
    painter.drawRoundedRect(QRectF(105, 76, 43, 24), 9, 9)  # long muzzle

    ears = QPainterPath()
    ears.moveTo(101, 65)
    ears.lineTo(106, 35)
    ears.lineTo(119, 58)
    ears.moveTo(119, 56)
    ears.lineTo(132, 37)
    ears.lineTo(134, 69)
    painter.drawPath(ears)

    # Beard and tail.
    beard = QPainterPath()
    beard.moveTo(110, 91)
    beard.lineTo(119, 116)
    beard.lineTo(128, 99)
    beard.lineTo(137, 113)
    beard.lineTo(141, 93)
    beard.closeSubpath()
    painter.drawPath(beard)
    painter.setPen(QPen(fur, 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(39, 91), QPointF(22, 69))

    # Legs change slightly between fallback frames so animation remains visible.
    painter.setPen(QPen(fur, 13, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if sitting:
        painter.drawLine(QPointF(53, 111), QPointF(43, 134))
        painter.drawLine(QPointF(93, 112), QPointF(101, 135))
    else:
        painter.drawLine(QPointF(54, 113), QPointF(49 + step, 137))
        painter.drawLine(QPointF(94, 113), QPointF(98 - step, 137))
    if waving:
        painter.drawLine(QPointF(102, 94), QPointF(89, 69))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(highlight)
    painter.drawEllipse(QRectF(52, body_y + 8, 43, 9))
    painter.setBrush(eye)
    painter.drawEllipse(QRectF(123, 69, 4.5, 4.5))
    painter.setBrush(QColor("#050506"))
    painter.drawEllipse(QRectF(142, 79, 8, 8))
    painter.end()
    return pixmap

