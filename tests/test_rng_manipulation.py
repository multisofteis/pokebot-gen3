import unittest

from modules.rng_manipulation import (
    SearchCriteria,
    advance_seed,
    generate_method1,
    next_seed,
    previous_seed,
    search_method1,
    recover_method1_pre_pid_seed,
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
                SearchCriteria(nature="Quirky", min_ivs=(17, 19, 20, 16, 13, 12)),
                limit=1,
            )
        )
        self.assertTrue(matches)
        self.assertEqual(matches[0].advance, 0)
        self.assertEqual(matches[0].ivs, (17, 19, 20, 16, 13, 12))


    def test_recover_method1_pre_pid_seed(self):
        frame = generate_method1(0x2031F790)
        self.assertEqual(recover_method1_pre_pid_seed(frame.pid, frame.ivs), 0x2031F790)

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
