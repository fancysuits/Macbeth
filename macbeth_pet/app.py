"""Application bootstrap and command-line options."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import signal
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from .animations import load_sprite_set
from .pet_window import PetWindow

SPRITE_FILENAME = "scottish_terrier_sprites.png"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Macbeth macOS Screen Pet")
    parser.add_argument(
        "--sprite",
        type=Path,
        help=f"Path to a 3×3 PNG sprite sheet (default: {SPRITE_FILENAME})",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=160,
        help="Pet window size in points/pixels (default: 160)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable diagnostic logging")
    return parser


def find_sprite(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path.expanduser().resolve()

    candidates = [
        Path.cwd() / SPRITE_FILENAME,
        Path(__file__).resolve().parent.parent / SPRITE_FILENAME,
    ]
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.insert(0, Path(bundle_root) / SPRITE_FILENAME)

    executable = Path(sys.executable).resolve()
    candidates.append(executable.parent / SPRITE_FILENAME)
    # Also support a PNG placed beside Macbeth.app in Finder.
    if ".app" in executable.as_posix():
        app_index = next(
            (index for index, part in enumerate(executable.parts) if part.endswith(".app")),
            None,
        )
        if app_index is not None:
            app_path = Path(*executable.parts[: app_index + 1])
            candidates.append(app_path.parent / SPRITE_FILENAME)

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    if not 64 <= args.size <= 512:
        raise SystemExit("--size must be between 64 and 512")

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Macbeth")
    app.setOrganizationName("Macbeth Screen Pet")
    app.setQuitOnLastWindowClosed(True)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())

    sprite_path = find_sprite(args.sprite)
    sprites = load_sprite_set(sprite_path, args.size)
    window = PetWindow(sprites, args.size)
    window.show()
    return app.exec()

