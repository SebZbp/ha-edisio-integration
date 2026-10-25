"""Options flow ("Configure" on the Dongle): a menu with one branch per Device operation.

Each branch lives in its own module as a mixin holding its steps, so branches can be
developed independently:

    options_add.py     AddDeviceSteps     async_step_add_device     (edisio-zmz.1)
    options_edit.py    EditDeviceSteps    async_step_edit_device    (edisio-zmz.2, .3)
    options_remove.py  RemoveDeviceSteps  async_step_remove_device  (edisio-zmz.4)

The menu entries below are the step ids; their labels are in strings.json under
``options.step.init.menu_options``.
"""
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .options_add import AddDeviceSteps
from .options_edit import EditDeviceSteps
from .options_remove import RemoveDeviceSteps


class EdisioOptionsFlow(
    AddDeviceSteps, EditDeviceSteps, RemoveDeviceSteps, config_entries.OptionsFlow
):
    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_device", "edit_device", "remove_device"],
        )

    def _save_devices(self, devices: Dict[str, Dict[str, Any]]) -> FlowResult:
        """Write the configured Devices to the options; the update listener reloads the entry."""
        new_options = dict(self.config_entry.options)
        new_options["devices"] = devices
        return self.async_create_entry(title="", data=new_options)
