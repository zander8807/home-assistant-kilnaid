"""Data models for KilnAid."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


@dataclass(frozen=True, slots=True)
class KilnData:
    """Normalized data for one kiln."""

    serial: str
    name: str
    external_id: str | None
    raw: dict[str, Any]

    @classmethod
    def from_api(
        cls, raw: dict[str, Any], names: dict[str, str]
    ) -> KilnData | None:
        """Create a kiln from a /kilns/view item."""
        serial_value = raw.get("serial_number")
        if not isinstance(serial_value, (str, int)) or not str(serial_value):
            return None
        serial = str(serial_value)
        external = raw.get("external_id")
        name = names.get(serial) or raw.get("name") or f"Kiln {serial}"
        return cls(
            serial=serial,
            name=str(name),
            external_id=str(external) if external is not None else None,
            raw=raw,
        )

    @property
    def status(self) -> dict[str, Any]:
        return _dict(self.raw.get("status"))

    @property
    def firing(self) -> dict[str, Any]:
        return _dict(self.status.get("firing"))

    @property
    def config(self) -> dict[str, Any]:
        return _dict(self.raw.get("config"))

    @property
    def diagnostics(self) -> dict[str, Any]:
        return _dict(self.status.get("diag"))

    @property
    def program_data(self) -> dict[str, Any]:
        return _dict(self.raw.get("program"))

    @property
    def mode(self) -> str:
        value = self.raw.get("mode") or self.status.get("mode") or "Not Connected"
        return str(value)

    @property
    def temperature_unit(self) -> str:
        value = self.config.get("t_scale") or self.firing.get("t_scale") or "F"
        return "°C" if str(value).upper() == "C" else "°F"

    @property
    def zone_count(self) -> int:
        value = _integer(self.config.get("num_zones"))
        return value if value in (1, 2, 3) else 1

    def temperature(self, zone: int) -> float | None:
        return _number(self.status.get(f"t{zone}") or self.raw.get(f"t{zone}"))

    @property
    def chamber_temperature(self) -> float | None:
        return self.temperature(2) or self.temperature(1)

    @property
    def setpoint(self) -> float | None:
        return _number(self.firing.get("set_pt") or self.firing.get("set_point"))

    @property
    def program(self) -> str | None:
        value = self.program_data.get("name") or self.raw.get("program_name")
        return str(value) if value not in (None, "") else None

    @property
    def segment(self) -> str | None:
        value = self.firing.get("step")
        return str(value) if value not in (None, "") else None

    @property
    def firing_seconds(self) -> int | None:
        hours = _integer(self.firing.get("fire_hour"))
        minutes = _integer(self.firing.get("fire_min"))
        if hours is None and minutes is None:
            return None
        return max(0, hours or 0) * 3600 + max(0, minutes or 0) * 60

    @property
    def hold_remaining_seconds(self) -> int | None:
        hours = _integer(self.firing.get("hold_hour"))
        minutes = _integer(self.firing.get("hold_min"))
        if hours is None and minutes is None:
            return None
        return max(0, hours or 0) * 3600 + max(0, minutes or 0) * 60

    @property
    def updated_at(self) -> datetime | None:
        value = self.raw.get("updatedAt") or self.raw.get("updated_at")
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @property
    def connected(self) -> bool:
        if self.mode == "Not Connected" or self.updated_at is None:
            return False
        return (datetime.now(timezone.utc) - self.updated_at).total_seconds() <= 300

    @property
    def error(self) -> bool:
        return self.mode == "Error" or bool(self.status.get("error"))

    @property
    def error_number(self) -> int | None:
        return _integer(_dict(self.status.get("error")).get("err_num"))

    @property
    def error_text(self) -> str | None:
        value = _dict(self.status.get("error")).get("err_text")
        return str(value) if value not in (None, "") else None

    @property
    def firmware(self) -> str | None:
        value = self.status.get("fw")
        return str(value) if value not in (None, "") else None

    @property
    def total_firings(self) -> int | None:
        return _integer(self.status.get("num_fire") or self.raw.get("total_firings"))

    def diagnostic_number(self, key: str, divisor: float = 1) -> float | None:
        value = _number(self.diagnostics.get(key))
        return value / divisor if value is not None else None

