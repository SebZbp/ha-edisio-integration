import asyncio
from typing import Dict, Any, Optional
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, BUTTON_CONFIGS, DEFAULT_ACTIVE_BUTTONS

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    
    @callback
    def async_discover_device(data: Dict[str, Any]) -> None:
        device_id: str = data.get("id", "")
        entities = []
        entities.append(EdisioBatterySensor(device_id, config_entry.entry_id))
        
        configured_devices = config_entry.options.get("devices", {})
        device_cfg = configured_devices.get(device_id, {})
        active_buttons_cfg = device_cfg.get("active_buttons", DEFAULT_ACTIVE_BUTTONS)
        button_ids = BUTTON_CONFIGS.get(active_buttons_cfg, [])
        for index, button_id in enumerate(button_ids):
            entities.append(EdisioButtonSensor(device_id, button_id, index + 1, config_entry.entry_id))
            
        async_add_entities(entities, update_before_add=False)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, f"{DOMAIN}_discover", async_discover_device)
    )
    
    # Set up sensors for all configured devices from config entry options
    configured_devices = config_entry.options.get("devices", {})
    for device_id, device_cfg in configured_devices.items():
        if device_id not in hass.data[DOMAIN][config_entry.entry_id]["devices"]:
            hass.data[DOMAIN][config_entry.entry_id]["devices"].add(device_id)
            
        entities = []
        entities.append(EdisioBatterySensor(device_id, config_entry.entry_id))
        
        active_buttons_cfg = device_cfg.get("active_buttons", DEFAULT_ACTIVE_BUTTONS)
        button_ids = BUTTON_CONFIGS.get(active_buttons_cfg, [])
        for index, button_id in enumerate(button_ids):
            entities.append(EdisioButtonSensor(device_id, button_id, index + 1, config_entry.entry_id))
            
        async_add_entities(entities)

class EdisioBatterySensor(SensorEntity):
    _attr_has_entity_name: bool = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement: str = PERCENTAGE

    def __init__(self, device_id: str, entry_id: str) -> None:
        self._device_id: str = device_id
        self._entry_id: str = entry_id
        self._attr_unique_id: str = f"{device_id}_battery"
        self._attr_name: str = "Battery"
        self._attr_native_value: int | None = None

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Edisio EBP8-B {self._device_id}",
            "manufacturer": "Edisio",
            "model": "EBP8-B",
            "via_device": (DOMAIN, self._entry_id)
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                f"{DOMAIN}_update_{self._device_id}", 
                self._update_battery
            )
        )

    @callback
    def _update_battery(self, data: Dict[str, Any]) -> None:
        battery_level: str | None = data.get("battery")
        if battery_level is not None:
            try:
                self._attr_native_value = min(100, int(battery_level))
                self.async_write_ha_state()
            except ValueError:
                pass

class EdisioButtonSensor(SensorEntity):
    _attr_has_entity_name: bool = True

    def __init__(self, device_id: str, button_id: str, button_index: int, entry_id: str) -> None:
        self._device_id: str = device_id
        self._button_id: str = button_id
        self._entry_id: str = entry_id
        self._attr_unique_id: str = f"{device_id}_button_{button_id}"
        self._attr_name: str = f"Button {button_index}"
        self._attr_native_value: str = "normal"
        self._reset_task: Optional[asyncio.Task] = None

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Edisio EBP8-B {self._device_id}",
            "manufacturer": "Edisio",
            "model": "EBP8-B",
            "via_device": (DOMAIN, self._entry_id)
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self._device_id}",
                self._update_button
            )
        )

    @callback
    def _update_button(self, data: Dict[str, Any]) -> None:
        if data.get("button") != self._button_id:
            return

        action = data.get("action", "")
        press_type = "long-press" if action in ["up", "down"] else "short-press"

        if self._reset_task is not None:
            self._reset_task.cancel()
            self._reset_task = None

        self._attr_native_value = press_type
        self.async_write_ha_state()

        async def _async_reset():
            await asyncio.sleep(1)
            self._attr_native_value = "normal"
            self.async_write_ha_state()
            self._reset_task = None

        self._reset_task = self.hass.async_create_task(_async_reset())

    async def async_will_remove_from_hass(self) -> None:
        if self._reset_task is not None:
            self._reset_task.cancel()
            self._reset_task = None
