"""Persistent firing state machine; independent of Home Assistant."""
from __future__ import annotations

import math

GAP_SECONDS = 15 * 60
COOLING_SECONDS = 48 * 3600
VALID_MODES = {"Firing", "Idle", "Complete", "Error", "Stopped", "Cooling"}


class FiringArchive:
    """Keep observed fires, with honest boundaries and no invented readings."""

    def __init__(self, data=None):
        self.data = data if data is not None else {"kilns": {}, "imported": False}

    def observe(self, serial, *, timestamp, mode, temperature=None, unit="°F",
                program=None, segment=None, source="live", counter=None, elapsed=None):
        """Accept each controller report once. Unknown modes do not end a fire."""
        if mode not in VALID_MODES or not math.isfinite(timestamp):
            return False
        kiln = self.data["kilns"].setdefault(serial, {"fires": [], "last": None})
        last = kiln["last"]
        if last and timestamp <= last["timestamp"]:
            return False
        gap = bool(last and timestamp - last["timestamp"] > GAP_SECONDS)
        active = kiln["fires"][-1] if kiln["fires"] else None
        # A reset elapsed clock AND changed counter can reveal a missed boundary.
        reset = bool(last and mode == last["mode"] == "Firing"
                     and counter is not None and last.get("counter") is not None
                     and counter != last["counter"] and elapsed is not None
                     and last.get("elapsed") is not None and elapsed < last["elapsed"])
        if mode == "Firing" and (not last or last["mode"] != "Firing" or reset):
            if active and active["end"] is None:
                active["outcome"] = "End not observed"
                active["has_gaps"] = True
            active = {"id": f"{serial}:{timestamp:.6f}", "start": timestamp,
                      "end": None, "partial_start": not last or gap or reset,
                      "has_gaps": False, "outcome": "Firing", "program": program,
                      "unit": unit, "peak": None, "samples": [], "source": source}
            kiln["fires"].append(active)
        if active:
            if gap and (active["end"] is None or timestamp-active["end"] <= COOLING_SECONDS):
                active["has_gaps"] = True
            if last and last["mode"] == "Firing" and mode != "Firing":
                active["end"] = timestamp
                active["outcome"] = mode
            if mode == "Firing" and program:
                active["program"] = program
            within_window = active["end"] is None or timestamp-active["end"] <= COOLING_SECONDS
            if temperature is not None and math.isfinite(temperature) and within_window:
                value = temperature
                if unit != active["unit"]:
                    value = value * 9 / 5 + 32 if active["unit"] == "°F" else (value-32)*5/9
                active["samples"].append([round(timestamp*1000), round(value, 3), segment, mode])
                active["peak"] = value if active["peak"] is None else max(active["peak"], value)
        kiln["last"] = {"timestamp": timestamp, "mode": mode, "counter": counter, "elapsed": elapsed}
        return True
