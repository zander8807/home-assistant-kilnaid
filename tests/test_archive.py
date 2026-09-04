"""Regression tests for real firing lifecycle and persistence failures."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "archive", Path(__file__).parents[1]/"custom_components/kilnaid/archive.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.archive = module.FiringArchive()

    def observe(self, t, mode, **kw):
        return self.archive.observe("kiln", timestamp=t, mode=mode, **kw)

    @property
    def fires(self):
        return self.archive.data["kilns"]["kiln"]["fires"]

    def test_complete_fire_cooling_and_next_fire(self):
        self.observe(100, "Idle")
        self.observe(200, "Firing", temperature=100, program="Cone 6")
        self.observe(300, "Firing", temperature=2200)
        self.observe(400, "Complete", temperature=2190)
        self.observe(500, "Idle", temperature=200)
        self.observe(600, "Firing", temperature=100)
        self.assertEqual(len(self.fires), 2)
        self.assertFalse(self.fires[0]["partial_start"])
        self.assertEqual(self.fires[0]["end"], 400)
        self.assertEqual(self.fires[0]["peak"], 2200)
        self.assertEqual(self.fires[0]["program"], "Cone 6")
        self.assertEqual(len(self.fires[0]["samples"]), 4)

    def test_restart_and_unknown_do_not_split(self):
        self.observe(100, "Firing", temperature=100)
        self.assertFalse(self.observe(150, "Not Connected"))
        self.archive = module.FiringArchive(json.loads(json.dumps(self.archive.data)))
        self.observe(200, "Firing", temperature=200)
        self.assertEqual(len(self.fires), 1)
        self.assertTrue(self.fires[0]["partial_start"])
        self.assertFalse(self.observe(200, "Firing", temperature=200))
        self.assertFalse(self.observe(190, "Complete"))
        self.assertIsNone(self.fires[0]["end"])

    def test_missing_start_and_middle_gap(self):
        self.observe(100, "Idle")
        self.observe(2000, "Firing")
        self.observe(4000, "Firing")
        self.assertTrue(self.fires[0]["partial_start"])
        self.assertTrue(self.fires[0]["has_gaps"])

    def test_error_ends_and_cooling_is_bounded(self):
        self.observe(100, "Firing", temperature=100)
        self.observe(200, "Error", temperature=150)
        self.observe(200+48*3600+1, "Idle", temperature=75)
        self.assertEqual(self.fires[0]["outcome"], "Error")
        self.assertEqual(len(self.fires[0]["samples"]), 2)

    def test_units_and_invalid_values(self):
        self.observe(100, "Firing", temperature=32)
        self.observe(200, "Firing", temperature=100, unit="°C")
        self.observe(300, "Firing", temperature=float('nan'))
        self.assertEqual(self.fires[0]["peak"], 212)
        self.assertEqual(len(self.fires[0]["samples"]), 2)
        json.dumps(self.archive.data, allow_nan=False)

    def test_counter_and_clock_reset_detect_missed_fire(self):
        self.observe(100, "Firing", counter=1, elapsed=2000)
        self.observe(200, "Firing", counter=2, elapsed=10)
        self.assertEqual(len(self.fires), 2)
        self.assertEqual(self.fires[0]["outcome"], "End not observed")
        self.assertTrue(self.fires[1]["partial_start"])

    def test_multiple_kilns_are_isolated(self):
        self.observe(100, "Firing", temperature=100)
        self.archive.observe('other', timestamp=200, mode='Complete', temperature=200)
        self.assertIsNone(self.fires[0]['end'])
        self.assertEqual(self.archive.data['kilns']['other']['fires'], [])
