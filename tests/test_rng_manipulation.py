import unittest

from modules.rng_manipulation import (
    SearchCriteria,
    advance_seed,
    generate_method1,
    next_seed,
    previous_seed,
    search_method1,
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
        self.assertEqual(frame.pid, 59774)
        self.assertEqual(frame.nature, "Quirky")
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

    def test_shiny_filter_requires_ids(self):
        with self.assertRaises(ValueError):
            list(search_method1(0, 10, SearchCriteria(shiny=True), limit=1))


if __name__ == "__main__":
    unittest.main()
