from typing import Dict, Any, Callable
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    
    def async_discover_device(data: Dict[str, Any]) -> None:
        device_id: str = data.get("id", "")
        async_add_entities([EdisioBatterySensor(device_id)], update_before_add=False)

    async_dispatcher_connect(hass, f"{DOMAIN}_discover", async_discover_device)
    
    # Check if there are already devices in hass.data
    for device_id in hass.data[DOMAIN][config_entry.entry_id]["devices"]:
        async_add_entities([EdisioBatterySensor(device_id)])

class EdisioBatterySensor(SensorEntity):
    _attr_has_entity_name: bool = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement: str = PERCENTAGE

    def __init__(self, device_id: str) -> None:
        self._device_id: str = device_id
        self._attr_unique_id: str = f"{device_id}_battery"
        self._attr_name: str = "Battery"
        self._attr_native_value: int | None = None

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Edisio EBP8-B {self._device_id}",
            "manufacturer": "Edisio",
            "model": "EBP8-B"
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                f"{DOMAIN}_update_{self._device_id}", 
                self._update_battery
            )
        )

    def _update_battery(self, data: Dict[str, Any]) -> None:
        battery_level: str | None = data.get("battery")
        if battery_level is not None:
            try:
                self._attr_native_value = min(100, int(battery_level))
                self.async_write_ha_state()
            except ValueError:
                pass
