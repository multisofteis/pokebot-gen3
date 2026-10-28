import unittest

from modules.rng_manipulation import (
    SearchCriteria,
    advance_seed,
    generate_method1,
    next_seed,
    previous_seed,
    search_method1,
    recover_method1_pre_pid_seed,
    seed_was_passed,
    seed_distance,
)


class TestGen3RngManipulation(unittest.TestCase):
    def test_known_lcrng_transition(self):
        self.assertEqual(next_seed(0), 0x00006073)
        self.assertEqual(previous_seed(next_seed(0x12345678)), 0x12345678)

    def test_advance_and_reverse(self):
        seed = 0x2031F790
        self.assertEqual(advance_seed(advance_seed(seed, 1234), -1234), seed)

    def test_method1_generation_known_vector(self):
        frame = generate_method1(0, tid=0, sid=0)
        self.assertEqual(frame.pid, 0xE97E0000)
        self.assertEqual(frame.nature, "Naive")
        self.assertEqual(frame.ivs, (17, 19, 20, 16, 13, 12))
        self.assertEqual(frame.advance, 0)

    def test_search_respects_nature_and_iv_filters(self):
        matches = list(
            search_method1(
                0,
                1000,
                SearchCriteria(nature="Naive", min_ivs=(17, 19, 20, 16, 13, 12)),
                limit=1,
            )
        )
        self.assertTrue(matches)
        self.assertEqual(matches[0].advance, 0)
        self.assertEqual(matches[0].ivs, (17, 19, 20, 16, 13, 12))


    def test_seed_was_passed_between_observations(self):
        previous = 0x12345678
        target = advance_seed(previous, 3)
        current = advance_seed(previous, 5)
        self.assertTrue(seed_was_passed(previous, current, target))
        self.assertFalse(seed_was_passed(previous, current, advance_seed(previous, 6)))

    def test_seed_was_passed_handles_unusually_large_jump(self):
        previous = 0x12345678
        current = advance_seed(previous, 300)
        self.assertIsNone(seed_was_passed(previous, current, advance_seed(previous, 290), max_steps=256))
        self.assertEqual(seed_distance(current, advance_seed(previous, 290), max_steps=20000), -10)

    def test_recover_method1_pre_pid_seed(self):
        frame = generate_method1(0x2031F790)
        self.assertEqual(recover_method1_pre_pid_seed(frame.pid, frame.ivs), 0x2031F790)

    def test_recover_reported_firered_starter(self):
        pid = 0xD3B6443E
        ivs = (16, 20, 6, 2, 28, 27)
        self.assertEqual(recover_method1_pre_pid_seed(pid, ivs), 0x2AF3F43E)

    def test_gender_and_ability_filters(self):
        frame = generate_method1(0)
        criteria = SearchCriteria(
            gender="male",
            ability="Overgrow",
            species_abilities=("Overgrow",),
            gender_ratio=31,
        )
        matches = list(search_method1(0, 0, criteria, limit=1))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pid, frame.pid)

    def test_shiny_filter_requires_ids(self):
        with self.assertRaises(ValueError):
            list(search_method1(0, 10, SearchCriteria(shiny=True), limit=1))


if __name__ == "__main__":
    unittest.main()
