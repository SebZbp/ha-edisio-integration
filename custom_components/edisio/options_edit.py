"""Edit branch of the options flow (edisio-zmz.2 name/entity IDs/area, edisio-zmz.3 layout).

Steps:
    edit_device            pick a configured Device ("BP Cuisine (06708E57)")
    edit_device_settings   the edit form, one field per editable property. To add a field
                           (name, area, entity IDs, Button layout): add a field in ``_edit_schema``
                           and handle it in ``_apply_edit``.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    BUTTON_CONFIGS,
    CONF_ACTIVE_BUTTONS,
    CONF_AREA_ID,
    CONF_NAME,
    CONF_RADIO_ID,
    DEFAULT_ACTIVE_BUTTONS,
    DOMAIN,
)
from .device import build_device_cfg, device_name, device_picker_schema

_LOGGER = logging.getLogger(__name__)

CONF_UPDATE_ENTITY_IDS = "update_entity_ids"


class EditDeviceSteps:
    _edit_radio_id: str

    async def async_step_edit_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        devices: Dict[str, Dict[str, Any]] = self.config_entry.options.get("devices", {})
        if not devices:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            if user_input.get(CONF_RADIO_ID) not in devices:
                return self.async_abort(reason="unknown_device")
            self._edit_radio_id = user_input[CONF_RADIO_ID]
            return await self.async_step_edit_device_settings()
        return self.async_show_form(
            step_id="edit_device", data_schema=device_picker_schema(devices)
        )

    async def async_step_edit_device_settings(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        radio_id = self._edit_radio_id
        # The Device may have been removed since it was picked (e.g. from another session).
        if radio_id not in self.config_entry.options.get("devices", {}):
            return self.async_abort(reason="unknown_device")
        if user_input is None:
            return self.async_show_form(
                step_id="edit_device_settings",
                data_schema=self._edit_schema(radio_id),
                description_placeholders={"radio_id": radio_id},
            )
        new_cfg, skipped = self._apply_edit(radio_id, user_input)
        if skipped:
            # Reported, not overwritten; the edit itself succeeded, so it is not an abort.
            message = (
                f"Edisio Device {radio_id} was saved, but these entity IDs were not changed "
                f"because another entity already uses them: {', '.join(skipped)}"
            )
            _LOGGER.warning(message)
            persistent_notification.async_create(
                self.hass,
                message,
                title="Edisio: entity IDs not changed",
                notification_id=f"{DOMAIN}_entity_ids_skipped_{radio_id}",
            )
        devices = dict(self.config_entry.options["devices"])
        devices[radio_id] = new_cfg
        return self._save_devices(devices)

    def _edit_schema(self, radio_id: str) -> vol.Schema:
        cfg = self.config_entry.options["devices"][radio_id]
        device = self._registry_device(radio_id)
        return vol.Schema({
            vol.Required(
                CONF_ACTIVE_BUTTONS, default=cfg.get(CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
            vol.Optional(CONF_NAME, description={"suggested_value": cfg.get(CONF_NAME, "")}): str,
            vol.Optional(
                CONF_AREA_ID,
                description={"suggested_value": device.area_id if device else None},
            ): selector.AreaSelector(),
            vol.Optional(CONF_UPDATE_ENTITY_IDS, default=False): bool,
        })

    def _registry_device(self, radio_id: str):
        return dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, radio_id)})

    def _apply_edit(
        self, radio_id: str, user_input: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply the submitted form: registry changes now; returns the new stored config.

        Also returns the entity IDs that could not be set because another entity holds them.
        The caller has already checked that the Device is configured, so nothing here fails
        before the first registry change.
        """
        cfg = build_device_cfg(user_input, self.config_entry.options["devices"][radio_id])
        self._remove_dropped_buttons(radio_id, cfg[CONF_ACTIVE_BUTTONS])

        device = self._registry_device(radio_id)
        if device is not None:
            dr.async_get(self.hass).async_update_device(
                device.id,
                name=device_name(radio_id, cfg),
                name_by_user=None,
                # The submitted value is written: an empty/missing area clears the area.
                area_id=user_input.get(CONF_AREA_ID) or None,
            )
        skipped: List[str] = []
        if user_input.get(CONF_UPDATE_ENTITY_IDS):
            skipped = self._update_entity_ids(radio_id, device_name(radio_id, cfg))
        return cfg, skipped

    def _remove_dropped_buttons(self, radio_id: str, layout: int) -> None:
        """Remove Button sensors whose Button number is not in ``layout``; others are untouched.

        Entities for new Button numbers are created by the entry reload.
        """
        registry = er.async_get(self.hass)
        kept = {f"{radio_id}_button_{n}" for n in BUTTON_CONFIGS.get(layout, [])}
        prefix = f"{radio_id}_button_"
        for entity in er.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            if (entity.unique_id or "").startswith(prefix) and entity.unique_id not in kept:
                registry.async_remove(entity.entity_id)

    def _update_entity_ids(self, radio_id: str, name: str) -> List[str]:
        registry = er.async_get(self.hass)
        slug = slugify(name)
        prefix = f"{radio_id}_"
        skipped: List[str] = []
        for entity in er.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            if not (entity.unique_id or "").startswith(prefix):
                continue
            # "<radio id>_battery" -> "battery"; "<radio id>_button_03" -> "button_03"
            target = f"sensor.{slug}_{entity.unique_id[len(prefix):]}"
            if target == entity.entity_id:
                continue
            if registry.async_get(target) is not None:
                skipped.append(target)
                continue
            registry.async_update_entity(entity.entity_id, new_entity_id=target)
        return skipped
