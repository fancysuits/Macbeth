"""Transparent desktop window and user interactions for Macbeth."""

from __future__ import annotations

from pathlib import Path
import random
import sys
import tempfile
import time
import uuid

from PyQt6.QtCore import QPoint, QProcess, QRect, QTimer, Qt
from PyQt6.QtGui import (
    QAction,
    QCursor,
    QIcon,
    QImage,
    QMouseEvent,
    QPainter,
    QPixmap,
    QRegion,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QToolTip,
    QWidget,
)

from .animations import (
    ANIMATION_FRAMES,
    FRAME_INTERVAL_MS,
    SIT_FRAME_CHOICES,
    SpriteSet,
)
from .behavior import PetState, PetStateMachine
from .macos_overlay import configure_as_persistent_overlay
from .screenshot import add_sitting_watermark, next_screenshot_path, screenshot_directory


class PetWindow(QWidget):
    """A shaped, always-on-top window containing the animated pet."""

    TICK_MS = 40
    DRAG_DIRECTION_THRESHOLD = 7
    HOVER_SLEEP_SECONDS = 10.0
    HOVER_POSES = (1, 4)

    def __init__(self, sprites: SpriteSet, size: int = 160) -> None:
        super().__init__()
        self.sprites = sprites
        self.pet_size = size
        self.machine = PetStateMachine()
        self.machine.start(time.monotonic())

        self._visual_state = PetState.IDLE
        self._animation_index = 0
        self._last_frame_change = time.monotonic()
        self._current_pixmap = QPixmap()
        self._facing_left = False
        self._pose_frame = 0
        self._sit_frame = random.choice(SIT_FRAME_CHOICES)

        self._dragging = False
        self._drag_offset = QPoint()
        self._drag_direction_anchor_x = 0

        self._auto_until = 0.0
        self._auto_velocity = 0.0
        self._auto_next_decision = 0.0
        self._floating_x = 0.0

        self._screenshot_process: QProcess | None = None
        self._screenshot_temp_path = None
        self._hover_pose_until = 0.0

        self._configure_window()
        self._configure_menu_bar_icon()
        self._show_frame(force=True)
        self._place_at_bottom()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.TICK_MS)

    def _configure_window(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(self.pet_size, self.pet_size)
        self.setWindowTitle("Macbeth Screen Pet")

    def _configure_menu_bar_icon(self) -> None:
        self._tray_icon = QSystemTrayIcon(self)
        source = self.sprites.frame(4, facing_left=False)
        opaque_bounds = QRegion(source.mask()).boundingRect()
        icon_pixmap = source.copy(opaque_bounds) if not opaque_bounds.isEmpty() else source
        self._tray_icon.setIcon(QIcon(icon_pixmap))
        self._tray_icon.setToolTip("Macbeth")

        self._tray_menu = QMenu()
        self._add_menu_action(self._tray_menu, "Show Macbeth", self.show_pet)
        self._tray_menu.addSeparator()
        self._add_menu_action(self._tray_menu, "Wave", self._wave)
        self._add_menu_action(self._tray_menu, "Sit", self._sit)
        self._add_menu_action(self._tray_menu, "Screenshot", self._take_window_screenshot)
        self._add_menu_action(
            self._tray_menu,
            "Move on its own for 30 seconds",
            self._start_autonomous,
        )
        self._tray_menu.addSeparator()
        self._add_menu_action(
            self._tray_menu,
            "Quit Macbeth",
            QApplication.instance().quit,
        )
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._menu_bar_icon_activated)
        self._tray_icon.show()

    def _menu_bar_icon_activated(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            self.show_pet()

    def show_pet(self) -> None:
        """Bring Macbeth back from the menu bar without stealing focus."""
        self.show()
        self.raise_()
        QTimer.singleShot(0, self._enforce_overlay)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._enforce_overlay)

    def _enforce_overlay(self) -> None:
        configure_as_persistent_overlay(self)

    def _place_at_bottom(self) -> None:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.center().x() - self.width() // 2
        y = area.bottom() - self.height() + 1
        self.move(x, y)
        self._floating_x = float(x)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming convention
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self._current_pixmap)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        now = time.monotonic()
        if event.button() == Qt.MouseButton.LeftButton:
            self._cancel_hover_reaction()
            self._stop_autonomous(register_activity=False)
            self.machine.register_activity(now)
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_direction_anchor_x = event.globalPosition().toPoint().x()
            self._set_visual_state(PetState.RUN, now)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._dragging or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        global_point = event.globalPosition().toPoint()
        direction_delta = global_point.x() - self._drag_direction_anchor_x
        direction_changed = False
        if abs(direction_delta) >= self.DRAG_DIRECTION_THRESHOLD:
            new_facing_left = direction_delta < 0
            direction_changed = new_facing_left != self._facing_left
            self._facing_left = new_facing_left
            self._drag_direction_anchor_x = global_point.x()

        target = global_point - self._drag_offset
        target = self._clamp_to_available_screen(target, global_point)
        self.move(target)
        self._floating_x = float(target.x())
        if direction_changed:
            self._show_frame(force=True)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            now = time.monotonic()
            self.machine.register_activity(now)
            self._set_visual_state(PetState.IDLE, now)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._wave()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        if not self._dragging and not self._auto_until:
            self._begin_hover_reaction()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._cancel_hover_reaction()
        self.machine.register_activity(time.monotonic())
        menu = QMenu(self)
        self._add_menu_action(menu, "Wave", self._wave)
        self._add_menu_action(menu, "Rest", self._rest)
        self._add_menu_action(menu, "Sit", self._sit)
        self._add_menu_action(menu, "Random pose", self._random_pose)
        menu.addSeparator()
        self._add_menu_action(menu, "Screenshot", self._take_window_screenshot)
        menu.addSeparator()
        self._add_menu_action(menu, "Move on its own for 30 seconds", self._start_autonomous)
        menu.addSeparator()
        self._add_menu_action(menu, "Quit Macbeth", QApplication.instance().quit)
        menu.exec(event.globalPos())

    def _add_menu_action(self, menu: QMenu, label: str, callback) -> QAction:
        action = menu.addAction(label)
        action.triggered.connect(callback)
        return action

    def _wave(self) -> None:
        self._cancel_hover_reaction()
        self._stop_autonomous(register_activity=False)
        now = time.monotonic()
        self.machine.start_temporary(PetState.WAVE, now, 2.6)
        self._set_visual_state(PetState.WAVE, now)

    def _rest(self) -> None:
        self._cancel_hover_reaction()
        self._stop_autonomous(register_activity=False)
        now = time.monotonic()
        self.machine.start_temporary(PetState.REST, now, 10.0)
        self._set_visual_state(PetState.REST, now)

    def _sit(self) -> None:
        self._cancel_hover_reaction()
        self._stop_autonomous(register_activity=False)
        now = time.monotonic()
        self.machine.sit_now(now)
        self._set_visual_state(PetState.SIT, now)

    def _random_pose(self) -> None:
        self._cancel_hover_reaction()
        self._stop_autonomous(register_activity=False)
        now = time.monotonic()
        self._pose_frame = random.randrange(len(self.sprites.frames))
        self.machine.start_temporary(PetState.POSE, now, 4.0)
        self._set_visual_state(PetState.POSE, now)

    def _begin_hover_reaction(self) -> None:
        now = time.monotonic()
        self._pose_frame = random.choice(self.HOVER_POSES)
        self._hover_pose_until = now + self.HOVER_SLEEP_SECONDS
        self.machine.register_activity(now)
        self._set_visual_state(PetState.POSE, now)

    def _cancel_hover_reaction(self) -> None:
        self._hover_pose_until = 0.0

    def _take_window_screenshot(self) -> None:
        """Open macOS window selection, then save and copy a watermarked PNG."""
        if sys.platform != "darwin":
            self._show_screenshot_message("Window screenshots are available on macOS.")
            return
        if self._screenshot_process is not None:
            return

        self._stop_autonomous(register_activity=False)
        self.machine.register_activity(time.monotonic())
        self.hide()
        # Let the context menu and pet window disappear before macOS enters
        # its native window-selection mode.
        QTimer.singleShot(180, self._launch_screenshot_capture)

    def _launch_screenshot_capture(self) -> None:
        temporary_name = f"macbeth-capture-{uuid.uuid4().hex}.png"
        self._screenshot_temp_path = Path(tempfile.gettempdir()) / temporary_name

        process = QProcess(self)
        self._screenshot_process = process
        process.finished.connect(self._finish_screenshot_capture)
        process.errorOccurred.connect(self._screenshot_process_error)
        process.start(
            "/usr/sbin/screencapture",
            ["-i", "-W", "-x", str(self._screenshot_temp_path)],
        )

    def _finish_screenshot_capture(
        self,
        exit_code: int,
        _exit_status: QProcess.ExitStatus,
    ) -> None:
        process = self._screenshot_process
        temporary_path = self._screenshot_temp_path
        if process is None:
            return

        error_text = bytes(process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        ).strip()
        self._screenshot_process = None
        self._screenshot_temp_path = None
        process.deleteLater()
        self.show()
        self.raise_()

        if (
            exit_code != 0
            or temporary_path is None
            or not temporary_path.is_file()
            or temporary_path.stat().st_size == 0
        ):
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            message = "Screenshot cancelled."
            if error_text:
                message = "Screenshot failed. Check Screen Recording permission."
            self._show_screenshot_message(message)
            return

        try:
            screenshot = QImage(str(temporary_path))
            if screenshot.isNull():
                raise ValueError("macOS returned an unreadable screenshot")

            finished = add_sitting_watermark(
                screenshot,
                self.sprites.frame(6, facing_left=False),
            )
            directory = screenshot_directory()
            directory.mkdir(parents=True, exist_ok=True)
            destination = next_screenshot_path(directory)
            if not finished.save(str(destination), "PNG"):
                raise OSError(f"Could not save {destination}")

            QApplication.clipboard().setImage(finished)
            self._show_screenshot_message(
                f"Saved to {destination.name}\nCopied to clipboard."
            )
        except (OSError, ValueError) as error:
            self._show_screenshot_message(f"Screenshot failed: {error}")
        finally:
            temporary_path.unlink(missing_ok=True)

    def _screenshot_process_error(self, _error: QProcess.ProcessError) -> None:
        process = self._screenshot_process
        if process is None or process.state() != QProcess.ProcessState.NotRunning:
            return
        temporary_path = self._screenshot_temp_path
        self._screenshot_process = None
        self._screenshot_temp_path = None
        process.deleteLater()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        self.show()
        self.raise_()
        self._show_screenshot_message("Could not start the macOS screenshot tool.")

    def _show_screenshot_message(self, message: str) -> None:
        QToolTip.showText(QCursor.pos(), message, self)

    def _start_autonomous(self) -> None:
        self._cancel_hover_reaction()
        now = time.monotonic()
        self.machine.register_activity(now)
        self._auto_until = now + 30.0
        self._auto_next_decision = 0.0
        self._floating_x = float(self.x())
        self._choose_autonomous_motion(now)

    def _stop_autonomous(self, register_activity: bool = True) -> None:
        was_active = self._auto_until > 0.0
        self._auto_until = 0.0
        self._auto_velocity = 0.0
        if was_active and register_activity:
            self.machine.register_activity(time.monotonic())

    def _tick(self) -> None:
        now = time.monotonic()
        if self._dragging:
            self._advance_animation(now)
            return

        if self._auto_until:
            if now >= self._auto_until:
                self._stop_autonomous(register_activity=True)
            else:
                self._advance_autonomous(now)
                self._advance_animation(now)
                return

        if self._hover_pose_until:
            if now < self._hover_pose_until:
                self._set_visual_state(PetState.POSE, now)
                self._advance_animation(now)
                return
            self._hover_pose_until = 0.0
            self.machine.sleep_now(now)
            self._set_visual_state(PetState.SLEEP, now)

        desired_state = self.machine.update(now)
        self._set_visual_state(desired_state, now)
        self._advance_animation(now)

    def _advance_autonomous(self, now: float) -> None:
        if now >= self._auto_next_decision:
            self._choose_autonomous_motion(now)

        if self._auto_velocity == 0.0:
            self._set_visual_state(PetState.IDLE, now)
            return

        seconds = self.TICK_MS / 1000.0
        self._floating_x += self._auto_velocity * seconds
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        minimum = area.left()
        maximum = area.right() - self.width() + 1
        if self._floating_x <= minimum:
            self._floating_x = float(minimum)
            self._auto_velocity = abs(self._auto_velocity)
        elif self._floating_x >= maximum:
            self._floating_x = float(maximum)
            self._auto_velocity = -abs(self._auto_velocity)
        self._facing_left = self._auto_velocity < 0.0
        self.move(round(self._floating_x), self.y())
        moving_state = PetState.RUN if abs(self._auto_velocity) > 105 else PetState.WALK
        self._set_visual_state(moving_state, now)

    def _choose_autonomous_motion(self, now: float) -> None:
        self._auto_next_decision = now + random.uniform(1.2, 3.2)
        if random.random() < 0.2:
            self._auto_velocity = 0.0
            return
        speed = random.uniform(65.0, 130.0)
        self._auto_velocity = speed * random.choice((-1.0, 1.0))
        self._facing_left = self._auto_velocity < 0.0

    def _set_visual_state(self, state: PetState, now: float) -> None:
        if state == self._visual_state:
            return
        self._visual_state = state
        if state == PetState.SIT:
            self._sit_frame = random.choice(SIT_FRAME_CHOICES)
        self._animation_index = 0
        self._last_frame_change = now
        self._show_frame(force=True)

    def _advance_animation(self, now: float) -> None:
        interval = FRAME_INTERVAL_MS[self._visual_state] / 1000.0
        if now - self._last_frame_change < interval:
            return
        steps = max(1, int((now - self._last_frame_change) / interval))
        self._animation_index += steps
        self._last_frame_change += steps * interval
        self._show_frame(force=True)

    def _show_frame(self, force: bool = False) -> None:
        if self._visual_state == PetState.POSE:
            frame_number = self._pose_frame
        elif self._visual_state == PetState.SIT:
            frame_number = self._sit_frame
        else:
            sequence = ANIMATION_FRAMES[self._visual_state]
            frame_number = sequence[self._animation_index % len(sequence)]
        pixmap = self.sprites.frame(frame_number, self._facing_left)
        if force or pixmap.cacheKey() != self._current_pixmap.cacheKey():
            self._current_pixmap = pixmap
            # The native window only occupies opaque sprite pixels. Clicks in
            # transparent corners therefore continue to the app underneath.
            mask = pixmap.mask()
            if not mask.isNull():
                self.setMask(mask)
            else:
                self.clearMask()
            self.update()

    def _clamp_to_available_screen(self, target: QPoint, cursor: QPoint) -> QPoint:
        screen = QApplication.screenAt(cursor) or QApplication.primaryScreen()
        if screen is None:
            return target
        area: QRect = screen.availableGeometry()
        return QPoint(
            min(max(target.x(), area.left()), area.right() - self.width() + 1),
            min(max(target.y(), area.top()), area.bottom() - self.height() + 1),
        )

