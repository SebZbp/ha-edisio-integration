from typing import Any, Dict

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
