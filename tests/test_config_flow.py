import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.edisio.config_flow import EdisioConfigFlow
from custom_components.edisio.const import DOMAIN, CONF_ACTIVE_BUTTONS

@pytest.mark.asyncio
async def test_config_flow_device_steps():
    # Instantiate flow
    flow = EdisioConfigFlow()
    flow.hass = MagicMock(spec=HomeAssistant)
    
    # Mock current entries check
    flow._async_current_entries = MagicMock(return_value=[])
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    
    # 1. Test async_step_device
    result = await flow.async_step_device({"device_id": "01234567"})
    
    flow.async_set_unique_id.assert_called_once_with("edisio_01234567")
    flow._abort_if_unique_id_configured.assert_called_once()
    assert result["type"] == "form"
    assert result["step_id"] == "device_confirm"

    # 2. Test async_step_device_confirm submitting form
    mock_entry = MagicMock()
    mock_entry.options = {}
    flow._async_current_entries = MagicMock(return_value=[mock_entry])
    
    result2 = await flow.async_step_device_confirm(user_input={"active_buttons": 4})
    
    assert result2["type"] == "abort"
    assert result2["reason"] == "device_configured"
    assert result2["description_placeholders"] == {"device_id": "01234567"}
    
    # Verify the options update is triggered
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        mock_entry,
        options={"devices": {"01234567": {"active_buttons": 4}}}
    )
