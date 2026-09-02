"""Sensors for KilnAid."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KilnAidRuntimeData
from .coordinator import KilnAidCoordinator
from .entity import KilnAidEntity
from .models import KilnData


@dataclass(frozen=True, kw_only=True)
class KilnAidSensorDescription(SensorEntityDescription):
    """Describe a KilnAid sensor."""

    value_fn: Callable[[KilnData], Any]
    exists_fn: Callable[[KilnData], bool] = lambda kiln: True


SENSORS: tuple[KilnAidSensorDescription, ...] = (
    KilnAidSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda kiln: kiln.chamber_temperature,
    ),
    KilnAidSensorDescription(
        key="setpoint",
        translation_key="setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda kiln: kiln.setpoint,
    ),
    KilnAidSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda kiln: kiln.mode,
    ),
    KilnAidSensorDescription(
        key="program",
        translation_key="program",
        value_fn=lambda kiln: kiln.program,
    ),
    KilnAidSensorDescription(
        key="segment",
        translation_key="segment",
        value_fn=lambda kiln: kiln.segment,
    ),
    KilnAidSensorDescription(
        key="firing_time",
        translation_key="firing_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda kiln: kiln.firing_seconds,
    ),
    KilnAidSensorDescription(
        key="hold_remaining",
        translation_key="hold_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda kiln: kiln.hold_remaining_seconds,
    ),
    KilnAidSensorDescription(
        key="total_firings",
        translation_key="total_firings",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda kiln: kiln.total_firings,
    ),
    KilnAidSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda kiln: kiln.updated_at,
    ),
    KilnAidSensorDescription(
        key="board_temperature",
        translation_key="board_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda kiln: kiln.diagnostic_number("board_t"),
        exists_fn=lambda kiln: kiln.diagnostic_number("board_t") is not None,
    ),
)


def _diagnostic_descriptions(kiln: KilnData) -> list[KilnAidSensorDescription]:
    descriptions: list[KilnAidSensorDescription] = []
    for zone in range(1, kiln.zone_count + 1):
        descriptions.extend(
            [
                KilnAidSensorDescription(
                    key=f"zone_{zone}_temperature",
                    translation_key="zone_temperature",
                    translation_placeholders={"zone": str(zone)},
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_registry_enabled_default=False,
                    value_fn=lambda data, zone=zone: data.temperature(zone),
                ),
                KilnAidSensorDescription(
                    key=f"zone_{zone}_current",
                    translation_key="zone_current",
                    translation_placeholders={"zone": str(zone)},
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_registry_enabled_default=False,
                    value_fn=lambda data, zone=zone: data.diagnostic_number(f"a{zone}"),
                    exists_fn=lambda data, zone=zone: (
                        data.diagnostic_number(f"a{zone}") is not None
                    ),
                ),
                KilnAidSensorDescription(
                    key=f"zone_{zone}_voltage",
                    translation_key="zone_voltage",
                    translation_placeholders={"zone": str(zone)},
                    device_class=SensorDeviceClass.VOLTAGE,
                    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_registry_enabled_default=False,
                    value_fn=lambda data, zone=zone: data.diagnostic_number(f"v{zone}", 100),
                    exists_fn=lambda data, zone=zone: (
                        data.diagnostic_number(f"v{zone}") is not None
                    ),
                ),
            ]
        )
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up KilnAid sensors."""
    runtime: KilnAidRuntimeData = entry.runtime_data
    coordinator = runtime.coordinator
    entities: list[KilnAidSensor] = []
    for serial, kiln in coordinator.data.items():
        descriptions = [*SENSORS, *_diagnostic_descriptions(kiln)]
        entities.extend(
            KilnAidSensor(coordinator, serial, description)
            for description in descriptions
            if description.exists_fn(kiln)
        )
    async_add_entities(entities)


class KilnAidSensor(KilnAidEntity, SensorEntity):
    """Representation of one KilnAid sensor."""

    entity_description: KilnAidSensorDescription

    def __init__(
        self,
        coordinator: KilnAidCoordinator,
        serial: str,
        description: KilnAidSensorDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        kiln = self.kiln
        return self.entity_description.value_fn(kiln) if kiln else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            return self.kiln.temperature_unit if self.kiln else None
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "status" or self.kiln is None:
            return None
        return {
            "alarm": self.kiln.status.get("alarm"),
            "error_number": self.kiln.error_number,
            "error_text": self.kiln.error_text,
        }
