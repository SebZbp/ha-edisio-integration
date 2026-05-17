from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    
    def async_discover_device(data):
        device_id = data.get("id")
        async_add_entities([EdisioBatterySensor(device_id)])

    async_dispatcher_connect(hass, f"{DOMAIN}_discover", async_discover_device)
    
    # Check if there are already devices in hass.data
    for device_id in hass.data[DOMAIN][config_entry.entry_id]["devices"]:
        async_add_entities([EdisioBatterySensor(device_id)])

class EdisioBatterySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device_id):
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_battery"
        self._attr_name = "Battery"
        self._attr_native_value = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Edisio EBP8-B {self._device_id}",
            "manufacturer": "Edisio",
            "model": "EBP8-B"
        }

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                f"{DOMAIN}_update_{self._device_id}", 
                self._update_battery
            )
        )

    def _update_battery(self, data):
        battery_level = data.get("battery")
        if battery_level is not None:
            # Simple conversion: 3.3V roughly 100%, though battery string is '139' (which was 4.6V?)
            # Usually CR2430 is 3V. If battery gives string representation, we convert to percentage.
            # For simplicity, we just set the raw value or percentage if mapped.
            try:
                # Edisio battery calculation from plugin: int((bl / 3.3) * 10)
                # Max 3.3V => 100.
                self._attr_native_value = min(100, int(battery_level))
                self.async_write_ha_state()
            except ValueError:
                pass
