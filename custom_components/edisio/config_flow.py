import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components import usb

from .const import DOMAIN, CONF_SERIAL_PORT, CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS

_LOGGER = logging.getLogger(__name__)

class EdisioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _serial_port: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        try:
            if self._async_current_entries():
                return self.async_abort(reason="single_instance_allowed")

            if user_input is not None:
                return self.async_create_entry(title="Edisio Dongle", data=user_input)

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_SERIAL_PORT): str}),
            )
        except Exception as e:
            _LOGGER.exception("Error in async_step_user: %s", e)
            raise

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        try:
            if self._async_current_entries():
                return self.async_abort(reason="single_instance_allowed")

            self._serial_port = discovery_info.device
            await self.async_set_unique_id(self._serial_port)
            self._abort_if_unique_id_configured()
            
            return await self.async_step_usb_confirm()
        except Exception as e:
            _LOGGER.exception("Error in async_step_usb: %s", e)
            raise

    async def async_step_usb_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        try:
            if user_input is not None:
                return self.async_create_entry(
                    title="Edisio Dongle", 
                    data={CONF_SERIAL_PORT: self._serial_port}
                )

            return self.async_show_form(
                step_id="usb_confirm",
                description_placeholders={"serial_port": self._serial_port or ""}
            )
        except Exception as e:
            _LOGGER.exception("Error in async_step_usb_confirm: %s", e)
            raise

    async def async_step_device(self, discovery_info: Dict[str, Any]) -> FlowResult:
        self._device_id = discovery_info["device_id"]
        await self.async_set_unique_id(f"edisio_{self._device_id}")
        self._abort_if_unique_id_configured()
        return await self.async_step_device_confirm()

    async def async_step_device_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            entries = self._async_current_entries()
            if entries:
                entry = entries[0]
                devices = dict(entry.options.get("devices", {}))
                devices[self._device_id] = {
                    "active_buttons": user_input["active_buttons"]
                }
                new_options = dict(entry.options)
                new_options["devices"] = devices
                self.hass.config_entries.async_update_entry(entry, options=new_options)
            return self.async_abort(
                reason="device_configured",
                description_placeholders={"device_id": self._device_id}
            )

        return self.async_show_form(
            step_id="device_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_ACTIVE_BUTTONS, default=DEFAULT_ACTIVE_BUTTONS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=5)
                )
            }),
            description_placeholders={"device_id": self._device_id}
        )
