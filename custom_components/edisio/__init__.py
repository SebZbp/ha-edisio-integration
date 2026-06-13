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
        @callback
        def async_handle_event(event_data: Dict[str, Any]) -> None:
            device_id: str = event_data.get("id", "")
            
            # Check if device is configured in options
            configured_devices = entry.options.get("devices", {})
            if device_id not in configured_devices:
                # Check if flow is already in progress
                in_progress = [
                    flow for flow in hass.config_entries.flow.async_progress()
                    if flow.get("handler") == DOMAIN and flow.get("context", {}).get("device_id") == device_id
                ]
                if not in_progress:
                    hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "device", "device_id": device_id},
                        data={"device_id": device_id}
                    )
                return

            # Fire edisio_button_event for automation triggers
            action: str = event_data.get("action", "")
            press_type: str = "long_press" if action in ["up", "down"] else "short_press"
            event_payload: Dict[str, str] = {
                "device_id": device_id,
                "button": event_data.get("button", ""),
                "type": press_type
            }
            hass.bus.async_fire("edisio_button_event", event_payload)
            
            # Handle device discovery and sensor updates
            if device_id not in hass.data[DOMAIN][entry.entry_id]["devices"]:
                hass.data[DOMAIN][entry.entry_id]["devices"].add(device_id)
                async_dispatcher_send(hass, f"{DOMAIN}_discover", event_data)
                
            async_dispatcher_send(hass, f"{DOMAIN}_update_{device_id}", event_data)

        hass.loop.call_soon_threadsafe(async_handle_event, data)

    hub.register_callback(handle_edisio_event)
    await hub.connect()
    
    # Reload integration when options change
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok