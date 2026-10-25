from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, CONF_NAME


def device_name(device_id: str, device_cfg: Dict[str, Any]) -> str:
    """The stored name of a Device, or "Edisio EBP8-B <Radio ID>" when none was given."""
    return device_cfg.get(CONF_NAME) or f"Edisio EBP8-B {device_id}"


def device_info(device_id: str, device_cfg: Dict[str, Any], entry_id: str) -> Dict[str, Any]:
    """Device registry info of a Device, linked to the Dongle."""
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": device_name(device_id, device_cfg),
        "manufacturer": "Edisio",
        "model": "EBP8-B",
        "via_device": (DOMAIN, entry_id),
    }


def apply_area(
    hass: HomeAssistant, entry_id: str, device_id: str, device_cfg: Dict[str, Any], area_id: str
) -> None:
    """Put a Device in an area, creating its registry entry if it does not exist yet.

    The area lives in the device registry only; it is never stored in the options.
    """
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry_id,
        **device_info(device_id, device_cfg, entry_id),
    )
    registry.async_update_device(device.id, area_id=area_id)
