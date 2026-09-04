"""Durable firing storage, recorder import and permission-checked history API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import partial
import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .archive import FiringArchive
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KilnHistory:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, 1, f"kilnaid.firings.{entry.entry_id}", atomic_writes=True)
        self.archive = FiringArchive()

    async def async_load(self):
        data = await self.store.async_load()
        self.archive = FiringArchive(data)
        if not self.archive.data.get("imported"):
            await self.async_import_recorder()

    async def async_import_recorder(self):
        """One-time import; missing/unavailable readings never terminate a fire."""
        if "recorder" not in self.hass.config.components:
            return
        from homeassistant.components.recorder import get_instance, history

        registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(registry, self.entry.entry_id)
        grouped = {}
        for entity in entries:
            for key in ("status", "temperature", "program", "segment", "last_update"):
                if entity.unique_id.endswith("_"+key):
                    serial = entity.unique_id[:-(len(key)+1)]
                    grouped.setdefault(serial, {})[key] = entity.entity_id
        ids = [entity_id for group in grouped.values() for entity_id in group.values()]
        if not ids:
            self.archive.data["imported"] = True
            await self.store.async_save(self.archive.data)
            return
        end = datetime.now(timezone.utc)
        try:
            data = await get_instance(self.hass).async_add_executor_job(partial(
                history.get_significant_states, self.hass, end-timedelta(days=30), end,
                entity_ids=ids, significant_changes_only=False,
            ))
        except Exception:  # Recorder failure must not disable live kiln monitoring.
            _LOGGER.exception("Unable to import retained kiln history; will retry on next reload")
            return
        for serial, entities in grouped.items():
            events = []
            for key, entity_id in entities.items():
                for state in data.get(entity_id, []):
                    if state.state not in ("unknown", "unavailable"):
                        events.append((state.last_updated.timestamp(), key, state))
            current = {}
            for timestamp, key, state in sorted(events, key=lambda e: e[0]):
                current[key] = state
                if key not in ("status", "temperature") or "status" not in current:
                    continue
                temp = current.get("temperature")
                if "last_update" in current:
                    try:
                        cloud_time = datetime.fromisoformat(current["last_update"].state).timestamp()
                        if timestamp-cloud_time > 300:
                            continue
                    except ValueError:
                        pass
                try:
                    value = float(temp.state) if key == "temperature" and temp else None
                except ValueError:
                    value = None
                self.archive.observe(
                    serial, timestamp=timestamp, mode=current["status"].state,
                    temperature=value,
                    unit=temp.attributes.get("unit_of_measurement", "°F") if temp else "°F",
                    program=current["program"].state if "program" in current else None,
                    segment=current["segment"].state if "segment" in current else None,
                    source="recorder",
                )
            # Metadata can arrive milliseconds after the last heating sample.
            fires = self.archive.data["kilns"].get(serial, {}).get("fires", [])
            for fire in fires:
                if not fire["program"]:
                    programs = data.get(entities.get("program"), [])
                    match = [s for s in programs if s.state not in ("unknown", "unavailable")
                             and s.last_updated.timestamp() <= (fire["end"] or end.timestamp())]
                    if match:
                        fire["program"] = match[-1].state
        self.archive.data["imported"] = True
        await self.store.async_save(self.archive.data)

    async def async_observe(self, kilns):
        changed = False
        now = datetime.now(timezone.utc).timestamp()
        for kiln in kilns:
            stamp = kiln.updated_at
            # Replayed stale cloud payloads are not fresh observations.
            if not stamp or not 0 <= now-stamp.timestamp() <= 900:
                continue
            changed |= self.archive.observe(
                kiln.serial, timestamp=stamp.timestamp(), mode=kiln.mode,
                temperature=kiln.chamber_temperature, unit=kiln.temperature_unit,
                program=kiln.program, segment=kiln.segment,
                counter=kiln.total_firings, elapsed=kiln.firing_seconds,
            )
        if changed:
            await self.store.async_save(self.archive.data)


async def async_setup_history(hass):
    """Register once; historical readings are never served as public static data."""
    websocket_api.async_register_command(hass, ws_history)
    await hass.http.async_register_static_paths([StaticPathConfig(
        "/kilnaid/kiln-history-card.js",
        str(Path(__file__).parent / "frontend" / "kiln-history-card.js"), False,
    )])


@websocket_api.websocket_command({
    vol.Required("type"): "kilnaid/firings",
    vol.Required("entity_id"): str,
    vol.Optional("firing_id"): str,
})
@websocket_api.async_response
async def ws_history(hass, connection, msg):
    """List summaries or retrieve one fire, respecting the source entity's access."""
    entity_id = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, "read"):
        connection.send_error(msg["id"], "unauthorized", "Entity access denied")
        return
    entity = er.async_get(hass).async_get(entity_id)
    if not entity or entity.platform != DOMAIN or not entity.unique_id.endswith("_status"):
        connection.send_error(msg["id"], "invalid_entity", "Choose a KilnAid status entity")
        return
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    runtime = getattr(entry, "runtime_data", None)
    serial = entity.unique_id[:-7]
    if runtime:
        data = runtime.coordinator.history.archive.data
    elif entry:
        # History remains readable even when cloud authentication/setup is failing.
        data = await Store(hass, 1, f"kilnaid.firings.{entry.entry_id}").async_load()
    else:
        data = None
    fires = (data or {}).get("kilns", {}).get(serial, {}).get("fires", [])
    if "firing_id" in msg:
        fire = next((f for f in fires if f["id"] == msg["firing_id"]), None)
        if fire is None:
            connection.send_error(msg["id"], "not_found", "Firing not found")
            return
        connection.send_result(msg["id"], fire)
    else:
        connection.send_result(msg["id"], {"fires": [
            {**{k: v for k, v in fire.items() if k != "samples"},
             "sample_count": len(fire["samples"])} for fire in reversed(fires)
        ]})
