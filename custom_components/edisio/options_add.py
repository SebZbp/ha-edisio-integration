"""Add branch of the options flow (edisio-zmz.1): configure a Device by typing its Radio ID."""
import re
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_ACTIVE_BUTTONS,
    CONF_AREA_ID,
    CONF_NAME,
    CONF_RADIO_ID,
    DEFAULT_ACTIVE_BUTTONS,
)
from .device import apply_area

_RADIO_ID = re.compile(r"[0-9A-F]{8}")


class AddDeviceSteps:
    async def async_step_add_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            radio_id = (user_input.get(CONF_RADIO_ID) or "").strip().upper()
            devices = dict(self.config_entry.options.get("devices", {}))
            if not _RADIO_ID.fullmatch(radio_id):
                errors[CONF_RADIO_ID] = "invalid_radio_id"
            elif radio_id in devices:
                errors[CONF_RADIO_ID] = "already_configured"
            else:
                device_cfg = {
                    CONF_ACTIVE_BUTTONS: user_input.get(CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS)
                }
                name = (user_input.get(CONF_NAME) or "").strip()
                if name:
                    device_cfg[CONF_NAME] = name
                devices[radio_id] = device_cfg
                area_id = user_input.get(CONF_AREA_ID)
                if area_id:
                    apply_area(self.hass, self.config_entry.entry_id, radio_id, device_cfg, area_id)
                for flow in self.hass.config_entries.flow.async_progress_by_handler(DOMAIN):
                    if flow["context"].get("device_id") == radio_id:
                        self.hass.config_entries.flow.async_abort(flow["flow_id"])
                return self._save_devices(devices)

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required(CONF_RADIO_ID): str,
                vol.Required(CONF_ACTIVE_BUTTONS, default=DEFAULT_ACTIVE_BUTTONS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=5)
                ),
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_AREA_ID): selector.AreaSelector(),
            }),
            errors=errors,
        )
