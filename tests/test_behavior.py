from unittest import TestCase

from macbeth_pet.behavior import PetState, PetStateMachine


class PetStateMachineTests(TestCase):
    def make_machine(self) -> PetStateMachine:
        return PetStateMachine(random_uniform=lambda low, high: 40.0)

    def test_inactivity_progresses_from_idle_to_sit_to_sleep(self) -> None:
        machine = self.make_machine()
        machine.start(100.0)

        self.assertEqual(machine.update(104.99), PetState.IDLE)
        self.assertEqual(machine.update(105.0), PetState.SIT)
        self.assertEqual(machine.update(144.99), PetState.SIT)
        self.assertEqual(machine.update(145.0), PetState.SLEEP)

    def test_activity_resets_a_sleeping_pet(self) -> None:
        machine = self.make_machine()
        machine.start(0.0)
        self.assertEqual(machine.update(45.0), PetState.SLEEP)

        machine.register_activity(45.0)
        self.assertEqual(machine.update(45.0), PetState.IDLE)

    def test_temporary_action_returns_to_fresh_idle_period(self) -> None:
        machine = self.make_machine()
        machine.start(0.0)
        machine.start_temporary(PetState.WAVE, now=10.0, duration=2.5)

        self.assertEqual(machine.update(12.49), PetState.WAVE)
        self.assertEqual(machine.update(12.5), PetState.IDLE)
        self.assertEqual(machine.update(17.49), PetState.IDLE)
        self.assertEqual(machine.update(17.5), PetState.SIT)

    def test_sit_now_sleeps_after_selected_delay(self) -> None:
        machine = self.make_machine()
        machine.start(0.0)
        machine.sit_now(10.0)

        self.assertEqual(machine.update(10.0), PetState.SIT)
        self.assertEqual(machine.update(49.99), PetState.SIT)
        self.assertEqual(machine.update(50.0), PetState.SLEEP)

    def test_sleep_now_stays_asleep(self) -> None:
        machine = self.make_machine()
        machine.start(0.0)
        machine.sleep_now(10.0)

        self.assertEqual(machine.update(10.0), PetState.SLEEP)
        self.assertEqual(machine.update(100.0), PetState.SLEEP)

