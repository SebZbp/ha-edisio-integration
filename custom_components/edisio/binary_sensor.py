from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .device import device_info
from .hub import EdisioHub
from .models import device_model

# An Opening sensor sends one of two commands per transition; either one sets the state,
# so a lost frame cannot lose a transition (spec: Recorded behaviour).
CLOSED_COMMANDS = {"01", "09"}
OPEN_COMMANDS = {"02", "0A"}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: EdisioHub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    async_add_entities([EdisioConnectionSensor(hub, config_entry.entry_id)])

    @callback
    def async_discover_device(data: Dict[str, Any]) -> None:
        device_id: str = data.get("id", "")
        device_cfg = config_entry.options.get("devices", {}).get(device_id, {})
        async_add_entities(_device_binary_sensors(device_id, device_cfg, config_entry.entry_id))

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, f"{DOMAIN}_discover", async_discover_device)
    )

    for device_id, device_cfg in config_entry.options.get("devices", {}).items():
        async_add_entities(_device_binary_sensors(device_id, device_cfg, config_entry.entry_id))


def _device_binary_sensors(device_id: str, device_cfg: Dict[str, Any], entry_id: str) -> List[BinarySensorEntity]:
    """The Open/Closed sensor of an Opening sensor; other Device models have none."""
    if not device_model(device_cfg).has_opening:
        return []
    return [EdisioOpeningSensor(device_id, entry_id, device_cfg)]


class EdisioOpeningSensor(BinarySensorEntity, RestoreEntity):
    """On means Open, off means Closed, unknown until the first report."""

    _attr_has_entity_name: bool = True
    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, device_id: str, entry_id: str, device_cfg: Optional[Dict[str, Any]] = None) -> None:
        self._device_cfg: Dict[str, Any] = device_cfg or {}
        self._device_id: str = device_id
        self._entry_id: str = entry_id
        self._attr_unique_id: str = f"{device_id}_opening"
        self._attr_is_on: bool | None = None

    @property
    def device_info(self) -> Dict[str, Any]:
        return device_info(self._device_id, self._device_cfg, self._entry_id)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restored first, so the next packet overrides it; never reported stays unknown.
        if (last := await self.async_get_last_state()) is not None and last.state in (STATE_ON, STATE_OFF):
            self._attr_is_on = last.state == STATE_ON
        self.async_on_remove(
            async_dispatcher_connect(self.hass, f"{DOMAIN}_update_{self._device_id}", self._update_state)
        )

    @callback
    def _update_state(self, data: Dict[str, Any]) -> None:
        cmd = data.get("cmd")
        if cmd in OPEN_COMMANDS:
            self._attr_is_on = True
        elif cmd in CLOSED_COMMANDS:
            self._attr_is_on = False
        else:
            return  # the Sensor button (2F) and anything else change no state
        self.async_write_ha_state()


class EdisioConnectionSensor(BinarySensorEntity):
    """Whether the Dongle's serial port is open; off while the Dongle is unplugged."""

    _attr_has_entity_name: bool = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll: bool = False

    def __init__(self, hub: EdisioHub, entry_id: str) -> None:
        self._hub: EdisioHub = hub
        self._entry_id: str = entry_id
        self._attr_unique_id: str = f"{entry_id}_connection"
        self._attr_name: str = "Connection"

    @property
    def device_info(self) -> Dict[str, Any]:
        return {"identifiers": {(DOMAIN, self._entry_id)}}

    @property
    def is_on(self) -> bool:
        return self._hub.connected

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_connection_{self._entry_id}",
                self._update_connection
            )
        )

    @callback
    def _update_connection(self) -> None:
        self.async_write_ha_state()
