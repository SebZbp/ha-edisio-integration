import pytest
import voluptuous as vol
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.edisio.config_flow import EdisioConfigFlow
from custom_components.edisio.const import DOMAIN, CONF_ACTIVE_BUTTONS
from custom_components.edisio.device import device_name

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
    result = await flow.async_step_device({"device_id": "01234567", "button": "05"})
    
    flow.async_set_unique_id.assert_called_once_with("edisio_01234567")
    flow._abort_if_unique_id_configured.assert_called_once()
    assert result["type"] == "form"
    assert result["step_id"] == "device_confirm"
    assert result["description_placeholders"] == {
        "device_id": "01234567",
        "button": "05",
    }

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


def _device_flow(entry_options=None):
    flow = EdisioConfigFlow()
    flow.hass = MagicMock(spec=HomeAssistant)
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    entry = MagicMock()
    entry.entry_id = "dongle"
    entry.options = entry_options or {}
    flow._async_current_entries = MagicMock(return_value=[entry])
    return flow, entry


async def _submit(flow, user_input):
    await flow.async_step_device({"device_id": "06708E57", "button": "05"})
    with patch("custom_components.edisio.device.dr.async_get") as mock_get:
        registry = mock_get.return_value
        await flow.async_step_device_confirm(user_input=user_input)
    return registry


@pytest.mark.asyncio
async def test_form_offers_optional_name_and_area_next_to_layout():
    flow, _ = _device_flow()
    result = await flow.async_step_device({"device_id": "06708E57", "button": "05"})
    keys = {str(k): k for k in result["data_schema"].schema}
    assert set(keys) == {"active_buttons", "name", "area_id"}
    assert isinstance(keys["name"], vol.Optional)
    assert isinstance(keys["area_id"], vol.Optional)
    assert isinstance(keys["active_buttons"], vol.Required)


@pytest.mark.asyncio
async def test_submitted_name_is_stored_trimmed_with_layout():
    flow, entry = _device_flow()
    await _submit(flow, {"active_buttons": 3, "name": "  BP Cuisine "})
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={"devices": {"06708E57": {"active_buttons": 3, "name": "BP Cuisine"}}},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "", "   "])
async def test_blank_or_missing_name_is_not_stored(name):
    flow, entry = _device_flow()
    user_input = {"active_buttons": 3}
    if name is not None:
        user_input["name"] = name
    await _submit(flow, user_input)
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry, options={"devices": {"06708E57": {"active_buttons": 3}}}
    )


@pytest.mark.asyncio
async def test_area_is_applied_to_registry_once_and_not_stored():
    flow, entry = _device_flow()
    registry = await _submit(
        flow, {"active_buttons": 5, "name": "BP Cuisine", "area_id": "kitchen"}
    )
    registry.async_get_or_create.assert_called_once()
    kwargs = registry.async_get_or_create.call_args.kwargs
    assert kwargs["identifiers"] == {(DOMAIN, "06708E57")}
    assert kwargs["name"] == "BP Cuisine"
    assert kwargs["via_device"] == (DOMAIN, "dongle")
    registry.async_update_device.assert_called_once_with(
        registry.async_get_or_create.return_value.id, area_id="kitchen"
    )
    options = flow.hass.config_entries.async_update_entry.call_args.kwargs["options"]
    assert "area_id" not in options["devices"]["06708E57"]


@pytest.mark.asyncio
async def test_no_area_leaves_registry_untouched():
    flow, _ = _device_flow()
    registry = await _submit(flow, {"active_buttons": 5})
    registry.async_update_device.assert_not_called()


def test_device_name_is_stored_name_or_default():
    assert device_name("06708E57", {"name": "BP Cuisine"}) == "BP Cuisine"
    assert device_name("06708E57", {"active_buttons": 5}) == "Edisio EBP8-B 06708E57"
    assert device_name("06708E57", {}) == "Edisio EBP8-B 06708E57"
