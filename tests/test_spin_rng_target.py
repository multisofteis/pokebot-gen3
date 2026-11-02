import unittest
from unittest.mock import patch

from modules.modes.util import higher_level_actions
from modules.rng_manipulation import SearchCriteria, advance_seed


class TestSpinToRngTargetTriggerAction(unittest.TestCase):
    def _successful_spin(self, **kwargs):
        yield
        return True

    def test_trigger_action_runs_once_synchronously_before_return(self):
        events = []
        callback = lambda: events.append("trigger")

        with patch.object(higher_level_actions, "read_live_rng_seed", return_value=0), patch.object(
            higher_level_actions, "spin", side_effect=self._successful_spin
        ):
            routine = higher_level_actions.spin_to_rng_target(
                SearchCriteria(),
                max_advances=0,
                trigger_action=callback,
            )
            next(routine)
            self.assertEqual(events, [])
            with self.assertRaises(StopIteration):
                next(routine)

        self.assertEqual(events, ["trigger"])

    def test_trigger_action_is_not_called_when_stopped_before_search(self):
        callback = unittest.mock.Mock()
        routine = higher_level_actions.spin_to_rng_target(
            SearchCriteria(),
            stop_condition=lambda: True,
            trigger_action=callback,
        )
        self.assertEqual(list(routine), [])
        callback.assert_not_called()

    def test_replanning_after_skipped_target_still_triggers_only_once(self):
        seeds = [0, advance_seed(0, 1)]
        outcomes = [False, True]
        callback = unittest.mock.Mock()

        def spin_with_outcomes(**kwargs):
            yield
            return outcomes.pop(0)

        with patch.object(
            higher_level_actions, "read_live_rng_seed", side_effect=seeds
        ), patch.object(
            higher_level_actions, "spin", side_effect=spin_with_outcomes
        ):
            routine = higher_level_actions.spin_to_rng_target(
                SearchCriteria(),
                max_advances=0,
                trigger_action=callback,
                max_replans=2,
            )
            result = list(routine)

        self.assertEqual(result, [None, None])
        callback.assert_called_once_with()

    def test_rejects_generator_callback(self):
        def yielding_callback():
            yield None

        with patch.object(higher_level_actions, "read_live_rng_seed", return_value=0), patch.object(
            higher_level_actions, "spin", side_effect=self._successful_spin
        ):
            routine = higher_level_actions.spin_to_rng_target(
                SearchCriteria(),
                max_advances=0,
                trigger_action=yielding_callback,
            )
            next(routine)
            with self.assertRaises(TypeError):
                next(routine)


if __name__ == "__main__":
    unittest.main()
