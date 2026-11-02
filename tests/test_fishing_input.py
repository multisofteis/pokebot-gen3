import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from modules.modes.util import higher_level_actions


class TestFishHumanInputHandling(unittest.TestCase):
    def test_continuous_fishing_presses_once_per_task_state(self):
        task = lambda state: SimpleNamespace(data=[state])
        task_states = [
            task(higher_level_actions.TaskFishing.WAIT_FOR_A.value),
            task(higher_level_actions.TaskFishing.WAIT_FOR_A.value),
            task(higher_level_actions.TaskFishing.WAIT_FOR_A.value),
            task(higher_level_actions.TaskFishing.START_ENCOUNTER.value),
            None,
            None,
        ]
        emulator = SimpleNamespace(press_button=Mock())

        with patch.object(higher_level_actions, "get_task", side_effect=task_states), patch.object(
            higher_level_actions.context, "emulator", emulator
        ):
            routine = higher_level_actions.fish(loop=True)
            for _ in task_states:
                next(routine)
            routine.close()

        self.assertEqual(
            [call.args[0] for call in emulator.press_button.call_args_list],
            ["A", "A", "Select"],
        )

    def test_continuous_fishing_reacts_again_if_a_state_reappears(self):
        task = lambda state: SimpleNamespace(data=[state])
        task_states = [
            task(higher_level_actions.TaskFishing.NOT_EVEN_NIBBLE.value),
            None,
            task(higher_level_actions.TaskFishing.NOT_EVEN_NIBBLE.value),
        ]
        emulator = SimpleNamespace(press_button=Mock())

        with patch.object(higher_level_actions, "get_task", side_effect=task_states), patch.object(
            higher_level_actions.context, "emulator", emulator
        ):
            routine = higher_level_actions.fish(loop=True)
            for _ in task_states:
                next(routine)
            routine.close()

        self.assertEqual(
            [call.args[0] for call in emulator.press_button.call_args_list],
            ["B", "Select", "B"],
        )

    def test_single_step_mode_keeps_one_frame_action(self):
        emulator = SimpleNamespace(press_button=Mock())
        with patch.object(higher_level_actions, "get_task", return_value=None), patch.object(
            higher_level_actions.context, "emulator", emulator
        ):
            routine = higher_level_actions.fish()
            next(routine)
            routine.close()

        emulator.press_button.assert_called_once_with("Select")


if __name__ == "__main__":
    unittest.main()
