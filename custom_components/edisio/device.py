from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_ACTIVE_BUTTONS, CONF_NAME, CONF_RADIO_ID, DEFAULT_ACTIVE_BUTTONS


def device_name(device_id: str, device_cfg: Dict[str, Any]) -> str:
    """The stored name of a Device, or "Edisio EBP8-B <Radio ID>" when none was given."""
    return device_cfg.get(CONF_NAME) or f"Edisio EBP8-B {device_id}"


def device_info(device_id: str, device_cfg: Dict[str, Any], entry_id: str) -> Dict[str, Any]:
    """Device registry info of a Device, linked to the Dongle."""
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": device_name(device_id, device_cfg),
        "manufacturer": "Edisio",
        "model": "EBP8",
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


def build_device_cfg(
    user_input: Dict[str, Any], current: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """The stored config of a Device from a submitted name + Button layout.

    ``current`` is the Device's existing config (when editing): its other keys are kept, its
    layout is the default when the submission has none, and an empty name clears the stored name.
    """
    cfg = dict(current or {})
    cfg[CONF_ACTIVE_BUTTONS] = user_input.get(
        CONF_ACTIVE_BUTTONS, cfg.get(CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS)
    )
    name = (user_input.get(CONF_NAME) or "").strip()
    if name:
        cfg[CONF_NAME] = name
    else:
        cfg.pop(CONF_NAME, None)
    return cfg


def device_picker_schema(devices: Dict[str, Dict[str, Any]]) -> vol.Schema:
    """Form schema to pick one configured Device, labelled "name (Radio ID)"."""
    return vol.Schema({
        vol.Required(CONF_RADIO_ID): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=radio_id, label=f"{device_name(radio_id, cfg)} ({radio_id})"
                    )
                    for radio_id, cfg in devices.items()
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    })
