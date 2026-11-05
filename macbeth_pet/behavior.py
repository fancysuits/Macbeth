"""Time-based behaviour for the pet, independent of the GUI toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import random
from typing import Callable


class PetState(Enum):
    """Every visual state understood by the animator."""

    IDLE = auto()
    SIT = auto()
    SLEEP = auto()
    WALK = auto()
    RUN = auto()
    WAVE = auto()
    REST = auto()
    POSE = auto()


@dataclass
class PetStateMachine:
    """Resolve inactivity and temporary actions into a visual state.

    The pet sits after ``sit_after`` seconds. Sleeping starts a random
    ``sleep_delay_range`` number of seconds after sitting, rather than after
    the initial interaction.
    """

    sit_after: float = 5.0
    sleep_delay_range: tuple[float, float] = (30.0, 60.0)
    random_uniform: Callable[[float, float], float] = field(
        default=random.uniform, repr=False
    )
    state: PetState = field(default=PetState.IDLE, init=False)
    last_activity: float = field(default=0.0, init=False)
    sleep_after: float = field(default=35.0, init=False)
    _temporary_state: PetState | None = field(default=None, init=False, repr=False)
    _temporary_until: float | None = field(default=None, init=False, repr=False)

    def start(self, now: float) -> None:
        """Start or restart the inactivity clock."""
        self.register_activity(now)

    def register_activity(self, now: float) -> None:
        """Return to idle and choose a fresh sleep deadline."""
        self.last_activity = now
        self.sleep_after = self.sit_after + self.random_uniform(
            *self.sleep_delay_range
        )
        self._temporary_state = None
        self._temporary_until = None
        self.state = PetState.IDLE

    def start_temporary(self, state: PetState, now: float, duration: float) -> None:
        """Show an explicit action, then restart the inactivity clock."""
        self._temporary_state = state
        self._temporary_until = now + max(0.0, duration)
        self.state = state

    def sit_now(self, now: float) -> None:
        """Enter sitting immediately and sleep 30–60 seconds from now."""
        self.register_activity(now - self.sit_after)
        self.state = PetState.SIT

    def sleep_now(self, now: float) -> None:
        """Enter sleep immediately and keep the inactivity clock asleep."""
        self._temporary_state = None
        self._temporary_until = None
        self.last_activity = now - self.sleep_after
        self.state = PetState.SLEEP

    def update(self, now: float) -> PetState:
        """Advance time and return the state that should be drawn."""
        if self._temporary_state is not None:
            assert self._temporary_until is not None
            if now < self._temporary_until:
                self.state = self._temporary_state
                return self.state
            self.register_activity(now)

        inactive_for = max(0.0, now - self.last_activity)
        if inactive_for < self.sit_after:
            self.state = PetState.IDLE
        elif inactive_for < self.sleep_after:
            self.state = PetState.SIT
        else:
            self.state = PetState.SLEEP
        return self.state

