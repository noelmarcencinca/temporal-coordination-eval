"""Design-invariant tests. Run: python -m unittest -v"""
import csv
import random
import tempfile
import unittest
from pathlib import Path

import numpy as np
import coordination_prototype as cp


class DesignTests(unittest.TestCase):
    def test_phase_matches_known_offsets_over_sampling_and_start_phases(self):
        # Different phases, offsets and sampling rates; analytic labels are the oracle.
        for frames in (8, 12, 24, 48):
            reverse = cp.reverse_cycle_indices(frames)
            for seed in range(20):
                for off in (0, 1, 15, 30, 60, 120, 179):
                    leg, arm, _ = cp.make_base(random.Random(seed), off, frames)
                    self.assertAlmostEqual(cp.phase_difference_deg(leg, arm), -off, places=8)
                    self.assertAlmostEqual(cp.phase_difference_deg(leg[reverse], arm[reverse]), off, places=8)

    def test_exact_pairs_and_same_start_and_control_inputs(self):
        trials = cp.build_trials([15, 30, 60], 3, 2, 12, 5)
        groups = {}
        for t in trials:
            groups.setdefault(t['group_id'], []).append(t)
        for pair in groups.values():
            if pair[0]['is_catch']:
                continue
            a, b = pair
            self.assertEqual({a['correct_answer'], b['correct_answer']}, {'ARM', 'LEG'})
            for mode in ('shuffled', 'single'):
                self.assertEqual(a['views'][mode], b['views'][mode])
            for segment in ('leg', 'arm'):
                x = a[segment][a['views']['ordered']]
                y = b[segment][b['views']['ordered']]
                np.testing.assert_array_equal(x[cp.reverse_cycle_indices(12)], y)
                self.assertEqual(x[0], y[0])

    def test_independent_pairs_and_seed_reproducibility(self):
        a = cp.build_trials([30], 4, 0, 12, 1)
        b = cp.build_trials([30], 4, 0, 12, 1)
        c = cp.build_trials([30], 4, 0, 12, 2)
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x['leg'], y['leg'])
            self.assertEqual(x['views'], y['views'])
        self.assertEqual(len({t['start_phase'] for t in a}), 4)
        self.assertNotEqual({t['start_phase'] for t in a}, {t['start_phase'] for t in c})

    def test_invalid_experimental_settings_rejected(self):
        for kwargs in ({'offsets':[0]}, {'offsets':[180]}, {'offsets':[-1]},
                       {'offsets':[float('nan')]}, {'offsets':[15, 15]},
                       {'frames':3}, {'cycles':2}, {'reps':0}, {'catch':-1}):
            settings = dict(offsets=[15], reps=1, catch=0, frames=12, cycles=1)
            settings.update(kwargs)
            with self.assertRaises(ValueError):
                cp.validate_config(**settings)

    def test_rendered_controls_and_blinded_response_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'generated'
            result = cp.generate(out, offsets=[30], reps=1, catch=1)
            self.assertEqual(result['total_images'], 9)
            self.assertTrue(result['paired_controls_byte_identical'])
            with (out / 'responses.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 9)
            for forbidden in ('correct_answer', 'direction', 'group_id', 'offset_deg'):
                self.assertNotIn(forbidden, rows[0])
            self.assertTrue(all(r['model_answer']=='' for r in rows))
            with self.assertRaises(ValueError):
                cp.generate(out, offsets=[30], reps=1, catch=1)


if __name__ == '__main__':
    unittest.main()
