import asyncio
from typing import Dict, Any, List
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, CONF_SERIAL_PORT
from .hub import EdisioHub

PLATFORMS: List[str] = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    port: str = entry.data.get(CONF_SERIAL_PORT, "")
    hub = EdisioHub(port)
    
    hass.data[DOMAIN][entry.entry_id] = {"port": port, "hub": hub, "devices": set()}

    # Register Edisio Dongle device in registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Edisio Dongle",
        manufacturer="Edisio",
        model="Dongle",
    )
    
    @callback
    def handle_edisio_event(data: Dict[str, Any]) -> None:
        device_id: str = data.get("id", "")
        
        # Fire edisio_button_event for automation triggers
        action: str = data.get("action", "")
        press_type: str = "long_press" if action in ["up", "down"] else "short_press"
        event_data: Dict[str, str] = {
            "device_id": device_id,
            "button": data.get("button", ""),
            "type": press_type
        }
        hass.bus.async_fire("edisio_button_event", event_data)
        
        # Handle device discovery and sensor updates
        if device_id not in hass.data[DOMAIN][entry.entry_id]["devices"]:
            hass.data[DOMAIN][entry.entry_id]["devices"].add(device_id)
            async_dispatcher_send(hass, f"{DOMAIN}_discover", data)
            
        async_dispatcher_send(hass, f"{DOMAIN}_update_{device_id}", data)

    hub.register_callback(handle_edisio_event)
    await hub.connect()
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok