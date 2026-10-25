"""Remove branch of the options flow (edisio-zmz.4): forget a configured Device."""
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_RADIO_ID
from .device import device_name


class RemoveDeviceSteps:
    async def async_step_remove_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        devices = dict(self.config_entry.options.get("devices", {}))
        if not devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            radio_id = user_input[CONF_RADIO_ID]
            if radio_id in devices:
                del devices[radio_id]
                registry = dr.async_get(self.hass)
                device = registry.async_get_device(identifiers={(DOMAIN, radio_id)})
                if device is not None:
                    # Also removes the device's entities from the entity registry.
                    registry.async_remove_device(device.id)
            return self._save_devices(devices)

        options = [
            selector.SelectOptionDict(
                value=radio_id, label=f"{device_name(radio_id, cfg)} ({radio_id})"
            )
            for radio_id, cfg in devices.items()
        ]
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required(CONF_RADIO_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
                ),
            }),
        )
