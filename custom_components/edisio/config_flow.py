from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components import usb

from .const import DOMAIN, CONF_SERIAL_PORT, CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS

class EdisioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _serial_port: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Edisio Dongle", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_SERIAL_PORT): str}),
        )

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        self._serial_port = discovery_info.device
        await self.async_set_unique_id(self._serial_port)
        self._abort_if_unique_id_configured()
        
        return await self.async_step_usb_confirm()

    async def async_step_usb_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Edisio Dongle", 
                data={CONF_SERIAL_PORT: self._serial_port}
            )

        return self.async_show_form(
            step_id="usb_confirm",
            description_placeholders={"serial_port": self._serial_port or ""}
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry
    ) -> config_entries.OptionsFlow:
        return EdisioOptionsFlowHandler(config_entry)

class EdisioOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ACTIVE_BUTTONS,
                    default=self.config_entry.options.get(CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5))
            })
        )
