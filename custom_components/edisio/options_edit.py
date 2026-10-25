"""Edit branch of the options flow (edisio-zmz.2 name/entity IDs/area, edisio-zmz.3 layout)."""
from typing import Any, Dict, Optional

from homeassistant.data_entry_flow import FlowResult


class EditDeviceSteps:
    async def async_step_edit_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        # Stub: replaced by edisio-zmz.2 / edisio-zmz.3.
        return self.async_abort(reason="not_implemented")
