"""Binary sensors for KilnAid."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KilnAidRuntimeData
from .coordinator import KilnAidCoordinator
from .entity import KilnAidEntity
from .models import KilnData


@dataclass(frozen=True, kw_only=True)
class KilnAidBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a KilnAid binary sensor."""

    value_fn: Callable[[KilnData], bool]


BINARY_SENSORS = (
    KilnAidBinarySensorDescription(
        key="firing",
        translation_key="firing",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda kiln: kiln.mode == "Firing",
    ),
    KilnAidBinarySensorDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda kiln: kiln.error,
    ),
    KilnAidBinarySensorDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda kiln: kiln.connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up KilnAid binary sensors."""
    runtime: KilnAidRuntimeData = entry.runtime_data
    async_add_entities(
        KilnAidBinarySensor(runtime.coordinator, serial, description)
        for serial in runtime.coordinator.data
        for description in BINARY_SENSORS
    )


class KilnAidBinarySensor(KilnAidEntity, BinarySensorEntity):
    """Representation of one KilnAid binary sensor."""

    entity_description: KilnAidBinarySensorDescription

    def __init__(
        self,
        coordinator: KilnAidCoordinator,
        serial: str,
        description: KilnAidBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.kiln) if self.kiln else None

