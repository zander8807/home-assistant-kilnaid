"""Tests for KilnAid payload normalization."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "kilnaid"
    / "models.py"
)
SPEC = importlib.util.spec_from_file_location("kilnaid_models", MODULE_PATH)
assert SPEC and SPEC.loader
MODELS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODELS
SPEC.loader.exec_module(MODELS)
KilnData = MODELS.KilnData


class KilnDataTest(unittest.TestCase):
    """Exercise payload normalization without requiring Home Assistant."""

    def test_normalizes_live_payload(self) -> None:
        """The fields observed in /kilns/view become stable model properties."""
        now = datetime.now(timezone.utc).isoformat()
        raw = {
            "serial_number": "1234",
            "external_id": "opaque-id",
            "updatedAt": now,
            "status": {
                "mode": "Firing",
                "t1": 1700,
                "t2": 1710,
                "t3": 1720,
                "fw": "4.9.0",
                "num_fire": 42,
                "alarm": "OFF",
                "firing": {
                    "set_pt": 1750,
                    "step": "Ramp 4",
                    "fire_hour": 7,
                    "fire_min": 5,
                    "hold_hour": 0,
                    "hold_min": 15,
                },
                "diag": {"a1": 12.5, "v1": 24125, "board_t": 95},
            },
            "config": {"t_scale": "F", "num_zones": 3},
            "program": {"name": "Cone 6"},
        }

        kiln = KilnData.from_api(raw, {"1234": "Studio Kiln"})

        self.assertIsNotNone(kiln)
        assert kiln is not None
        self.assertEqual(kiln.name, "Studio Kiln")
        self.assertEqual(kiln.mode, "Firing")
        self.assertTrue(kiln.connected)
        self.assertEqual(kiln.chamber_temperature, 1710)
        self.assertEqual(kiln.temperature(3), 1720)
        self.assertEqual(kiln.setpoint, 1750)
        self.assertEqual(kiln.program, "Cone 6")
        self.assertEqual(kiln.segment, "Ramp 4")
        self.assertEqual(kiln.firing_seconds, 7 * 3600 + 5 * 60)
        self.assertEqual(kiln.hold_remaining_seconds, 15 * 60)
        self.assertEqual(kiln.diagnostic_number("v1", 100), 241.25)

    def test_marks_old_cloud_data_disconnected(self) -> None:
        """A controller whose cloud timestamp is over five minutes old is offline."""
        old = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
        kiln = KilnData.from_api(
            {"serial_number": "1234", "updatedAt": old, "status": {"mode": "Idle"}},
            {},
        )

        self.assertIsNotNone(kiln)
        assert kiln is not None
        self.assertFalse(kiln.connected)

    def test_rejects_payload_without_serial_number(self) -> None:
        """Entities require a stable serial-number identifier."""
        self.assertIsNone(KilnData.from_api({"status": {"mode": "Idle"}}, {}))


if __name__ == "__main__":
    unittest.main()
