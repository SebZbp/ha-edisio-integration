import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components import usb
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_SERIAL_PORT, CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS, CONF_NAME, CONF_AREA_ID
from .device import apply_area, build_device_cfg, discovery_unique_id
from .models import OPENING_SENSOR, CONF_DEVICE_MODEL, discovery_title
from .options_flow import EdisioOptionsFlow

_LOGGER = logging.getLogger(__name__)

class EdisioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    _serial_port: Optional[str] = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> EdisioOptionsFlow:
        return EdisioOptionsFlow()

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        try:
            if self._async_current_entries():
                return self.async_abort(reason="single_instance_allowed")

            if user_input is not None:
                data = {**user_input, CONF_SERIAL_PORT: await self.hass.async_add_executor_job(usb.get_serial_by_id, user_input[CONF_SERIAL_PORT])}
                return self.async_create_entry(title="Edisio Dongle", data=data)

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_SERIAL_PORT): str}),
            )
        except Exception as e:
            _LOGGER.exception("Error in async_step_user: %s", e)
            raise

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        try:
            # An Ignored Device's entry is not a Dongle
            if self._async_current_entries(include_ignore=False):
                return self.async_abort(reason="single_instance_allowed")

            self._serial_port = await self.hass.async_add_executor_job(usb.get_serial_by_id, discovery_info.device)
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

    def _dongle_entry(self) -> Optional[config_entries.ConfigEntry]:
        """The Dongle's entry; entries of Ignored Devices are skipped."""
        entries = self._async_current_entries(include_ignore=False)
        return entries[0] if entries else None

    async def async_step_integration_discovery(self, discovery_info: Dict[str, Any]) -> FlowResult:
        self._device_id = discovery_info["device_id"]
        self._button = discovery_info.get("button", "")
        self._model_code = discovery_info.get("model_code", "")
        await self.async_set_unique_id(discovery_unique_id(self._device_id))
        self._abort_if_unique_id_configured()
        # Names the card, HA's Ignore confirmation and the ignored entry
        self.context["title_placeholders"] = {"name": discovery_title(self._device_id, self._model_code)}
        if self._model_code == OPENING_SENSOR.model_code:
            return await self.async_step_opening_sensor_confirm()
        return await self.async_step_device_confirm()

    async def async_step_opening_sensor_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            entry = self._dongle_entry()
            if entry:
                devices = dict(entry.options.get("devices", {}))
                device_cfg = build_device_cfg({**user_input, CONF_DEVICE_MODEL: OPENING_SENSOR.key})
                devices[self._device_id] = device_cfg
                area_id = user_input.get(CONF_AREA_ID)
                if area_id:
                    apply_area(self.hass, entry.entry_id, self._device_id, device_cfg, area_id)
                new_options = dict(entry.options)
                new_options["devices"] = devices
                self.hass.config_entries.async_update_entry(entry, options=new_options)
            return self.async_abort(
                reason="device_configured",
                description_placeholders={"device_id": self._device_id}
            )

        return self.async_show_form(
            step_id="opening_sensor_confirm",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_AREA_ID): selector.AreaSelector(),
            }),
            description_placeholders={"device_id": self._device_id},
        )

    async def async_step_device_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is not None:
            entry = self._dongle_entry()
            if entry:
                devices = dict(entry.options.get("devices", {}))
                device_cfg = build_device_cfg(user_input)
                devices[self._device_id] = device_cfg
                # The area is applied once, when the registry entry is created; it is not stored.
                area_id = user_input.get(CONF_AREA_ID)
                if area_id:
                    apply_area(self.hass, entry.entry_id, self._device_id, device_cfg, area_id)
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
                ),
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_AREA_ID): selector.AreaSelector(),
            }),
            description_placeholders={
                "device_id": self._device_id,
                "button": self._button,
            }
        )
