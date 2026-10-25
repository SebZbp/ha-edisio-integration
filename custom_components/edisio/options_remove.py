"""Remove branch of the options flow (edisio-zmz.4)."""
from typing import Any, Dict, Optional

from homeassistant.data_entry_flow import FlowResult


class RemoveDeviceSteps:
    async def async_step_remove_device(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        # Stub: replaced by edisio-zmz.4.
        return self.async_abort(reason="not_implemented")
