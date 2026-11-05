"""Small AppKit bridge used to keep the pet visible across macOS spaces."""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget


# NSWindow collection-behaviour flags from AppKit/NSWindow.h.
_CAN_JOIN_ALL_SPACES = 1 << 0
_MOVE_TO_ACTIVE_SPACE = 1 << 1
_STATIONARY = 1 << 4
_IGNORES_CYCLE = 1 << 6
_FULL_SCREEN_PRIMARY = 1 << 7
_FULL_SCREEN_AUXILIARY = 1 << 8
_FULL_SCREEN_NONE = 1 << 9

# The status-window level stays above normal, floating, and Dock windows while
# remaining below macOS pop-up menus, drag images, and security surfaces.
_NS_STATUS_WINDOW_LEVEL = 25


def configure_as_persistent_overlay(widget: QWidget) -> bool:
    """Apply native overlay behaviour to a visible top-level Qt widget."""
    if sys.platform != "darwin" or QGuiApplication.platformName() != "cocoa":
        return False

    try:
        view_pointer = int(widget.winId())
        if not view_pointer:
            return False

        objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        message_address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        if message_address is None:
            return False

        def selector(name: str) -> int:
            return int(objc.sel_registerName(name.encode("ascii")))

        send_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(message_address)
        send_void = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(message_address)
        send_bool = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_bool,
        )(message_address)
        send_integer = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_long,
        )(message_address)
        get_unsigned = ctypes.CFUNCTYPE(
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(message_address)
        send_unsigned = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )(message_address)

        # On Qt for macOS, QWidget.winId() is the native NSView. Its `window`
        # selector returns the containing NSWindow/NSPanel.
        window_pointer = send_pointer(view_pointer, selector("window"))
        if not window_pointer:
            return False

        send_integer(
            window_pointer,
            selector("setLevel:"),
            _NS_STATUS_WINDOW_LEVEL,
        )
        send_bool(window_pointer, selector("setHidesOnDeactivate:"), False)
        send_bool(window_pointer, selector("setCanHide:"), False)

        behaviour = get_unsigned(window_pointer, selector("collectionBehavior"))
        behaviour &= ~(
            _MOVE_TO_ACTIVE_SPACE | _FULL_SCREEN_PRIMARY | _FULL_SCREEN_NONE
        )
        behaviour |= (
            _CAN_JOIN_ALL_SPACES
            | _STATIONARY
            | _IGNORES_CYCLE
            | _FULL_SCREEN_AUXILIARY
        )
        send_unsigned(
            window_pointer,
            selector("setCollectionBehavior:"),
            behaviour,
        )
        send_void(window_pointer, selector("orderFrontRegardless"))
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        # Qt's cross-platform flags still provide a useful fallback if AppKit
        # internals are unavailable on a future macOS release.
        return False

