import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_SERIAL_PORT
from .hub import EdisioHub

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    port = entry.data.get(CONF_SERIAL_PORT)
    hub = EdisioHub(port)
    
    def handle_edisio_event(data: dict):
        # Fire edisio_button_event for automation triggers
        press_type = "long_press" if data.get("action") in ["up", "down"] else "short_press"
        event_data = {
            "device_id": data.get("id"),
            "button": data.get("button"),
            "type": press_type
        }
        hass.bus.async_fire("edisio_button_event", event_data)

    hub.register_callback(handle_edisio_event)
    await hub.connect()
    
    hass.data[DOMAIN][entry.entry_id] = {"port": port, "hub": hub}
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok