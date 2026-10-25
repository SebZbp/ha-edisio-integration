"""Edit branch of the options flow (edisio-zmz.2 name/entity IDs/area, edisio-zmz.3 layout).

Steps:
    edit_device            pick a configured Device ("BP Cuisine (06708E57)")
    edit_device_settings   the edit form, one field per editable property. To add a field
                           (e.g. Button layout, zmz.3): add it in ``_edit_schema`` and handle it
                           in ``_apply_edit``.
"""
from typing import Any, Dict, List, Optional

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import CONF_AREA_ID, CONF_NAME, CONF_RADIO_ID, DOMAIN
from .device import device_name

CONF_UPDATE_ENTITY_IDS = "update_entity_ids"


class EditDeviceSteps:
    _edit_radio_id: str
    _edited_cfg: Dict[str, Any]

    async def async_step_edit_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        devices: Dict[str, Dict[str, Any]] = self.config_entry.options.get("devices", {})
        if not devices:
            return self.async_abort(reason="no_devices")
        if user_input is not None and user_input.get(CONF_RADIO_ID) in devices:
            self._edit_radio_id = user_input[CONF_RADIO_ID]
            return await self.async_step_edit_device_settings()
        return self.async_show_form(
            step_id="edit_device",
            data_schema=vol.Schema({
                vol.Required(CONF_RADIO_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=[
                        {"value": rid, "label": f"{device_name(rid, cfg)} ({rid})"}
                        for rid, cfg in devices.items()
                    ])
                ),
            }),
        )

    async def async_step_edit_device_settings(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        radio_id = self._edit_radio_id
        if user_input is None:
            return self.async_show_form(
                step_id="edit_device_settings",
                data_schema=self._edit_schema(radio_id),
                description_placeholders={"radio_id": radio_id},
            )
        skipped = self._apply_edit(radio_id, user_input)
        devices = dict(self.config_entry.options.get("devices", {}))
        devices[radio_id] = self._edited_cfg
        if skipped:
            new_options = dict(self.config_entry.options)
            new_options["devices"] = devices
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
            return self.async_abort(
                reason="entity_ids_skipped",
                description_placeholders={"skipped": ", ".join(skipped)},
            )
        return self._save_devices(devices)

    def _edit_schema(self, radio_id: str) -> vol.Schema:
        cfg = self.config_entry.options["devices"][radio_id]
        device = self._registry_device(radio_id)
        return vol.Schema({
            vol.Optional(CONF_NAME, description={"suggested_value": cfg.get(CONF_NAME, "")}): str,
            vol.Optional(
                CONF_AREA_ID,
                description={"suggested_value": device.area_id if device else None},
            ): selector.AreaSelector(),
            vol.Optional(CONF_UPDATE_ENTITY_IDS, default=False): bool,
        })

    def _registry_device(self, radio_id: str):
        return dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, radio_id)})

    def _apply_edit(self, radio_id: str, user_input: Dict[str, Any]) -> List[str]:
        """Apply the submitted form: registry changes now, new stored config in ``_edited_cfg``.

        Returns the entity IDs that could not be set because another entity holds them.
        """
        cfg = dict(self.config_entry.options["devices"][radio_id])
        name = (user_input.get(CONF_NAME) or "").strip()
        if name:
            cfg[CONF_NAME] = name
        else:
            cfg.pop(CONF_NAME, None)
        self._edited_cfg = cfg

        device = self._registry_device(radio_id)
        if device is not None:
            dr.async_get(self.hass).async_update_device(
                device.id,
                name=device_name(radio_id, cfg),
                name_by_user=None,
                area_id=user_input.get(CONF_AREA_ID) or None,
            )
        if user_input.get(CONF_UPDATE_ENTITY_IDS):
            return self._update_entity_ids(radio_id, device_name(radio_id, cfg))
        return []

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
