from typing import Any, Dict
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN
from .hub import EdisioHub

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    hub: EdisioHub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    async_add_entities([EdisioConnectionSensor(hub, config_entry.entry_id)])


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
