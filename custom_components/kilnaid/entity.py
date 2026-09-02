"""Base entities for KilnAid."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KilnAidCoordinator
from .models import KilnData


class KilnAidEntity(CoordinatorEntity[KilnAidCoordinator]):
    """Base class for an entity belonging to one kiln."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KilnAidCoordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        self._attr_unique_id = f"{serial}_{key}"

    @property
    def kiln(self) -> KilnData | None:
        return self.coordinator.data.get(self.serial)

    @property
    def available(self) -> bool:
        return super().available and self.kiln is not None

    @property
    def device_info(self) -> DeviceInfo:
        kiln = self.kiln
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            name=kiln.name if kiln else f"Kiln {self.serial}",
            manufacturer="Bartlett Instrument",
            model="Genesis kiln controller",
            sw_version=kiln.firmware if kiln else None,
            configuration_url="https://kilnaid.bartinst.com/kilns",
        )

