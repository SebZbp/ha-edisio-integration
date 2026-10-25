# Edisio HA Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native Home Assistant integration for Edisio RF devices, focusing on the EBP8-B 8-button switch, USB discovery, and coexistence with RFPlayer.

**Architecture:** We will create an async Python library (`edisio_api.py`) to handle the serial parsing of the Edisio 433/868 MHz protocol. The integration layer will consume this library, provide a config flow for USB discovery and options (button counts), and expose diagnostic sensors and device triggers for HA automations.

**Tech Stack:** Python 3.12, Home Assistant custom component APIs, `pyserial-asyncio`, `pytest`.

---

### Task 1: Protocol Library `edisio_api.py` Parsing

**Files:**
- Create: `custom_components/edisio/edisio_api.py`
- Test: `tests/test_edisio_api.py`

- [ ] **Step 1: Write the failing test for packet validation**

```python
import pytest
from custom_components.edisio.edisio_api import test_edisio, decode_packet

def test_edisio_valid_packet():
    # A valid packet starts with 6C 76 63, ends with 64 0D 0A
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 64 0D 0A"
    assert test_edisio(packet) is True

def test_edisio_invalid_packet():
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 00 00 00"
    assert test_edisio(packet) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_edisio_api.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'custom_components.edisio'"

- [ ] **Step 3: Write minimal implementation in `edisio_api.py`**

```python
import binascii

def test_edisio(message: str) -> bool:
    message = message.replace(' ', '')
    try:
        int(message, 16)
        raw = binascii.unhexlify(message)
        if len(raw) < 16:
            return False
        if raw[0] != 0x6C or raw[1] != 0x76 or raw[2] != 0x63:
            return False
        if raw[-1] != 0x0A or raw[-2] != 0x0D or raw[-3] != 0x64:
            return False
        return True
    except Exception:
        return False

def decode_packet(message: str) -> dict:
    # Minimal skeleton for now
    if not test_edisio(message):
        return {}
    
    msg = message.replace(' ', '')
    pid = msg[6:14]
    mid = msg[16:18]
    bl = int(msg[18:20], 16)
    battery = str(int((bl / 3.3) * 10))
    cmd = msg[24:26]
    
    return {
        "id": pid,
        "mid": mid,
        "battery": battery,
        "cmd": cmd
    }
```

- [ ] **Step 4: Create `__init__.py` files to make module accessible**

```bash
mkdir -p custom_components/edisio tests
touch custom_components/__init__.py
touch custom_components/edisio/__init__.py
touch tests/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_edisio_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/ tests/
git commit -m "feat: add edisio protocol parsing core"
```

### Task 2: Integration Scaffolding and Manifest

**Files:**
- Create: `custom_components/edisio/manifest.json`
- Create: `custom_components/edisio/const.py`

- [ ] **Step 1: Write `manifest.json`**

```json
{
  "domain": "edisio",
  "name": "Edisio Smart Home",
  "version": "1.0.0",
  "documentation": "https://github.com/seb_zawadski/ha-edisio-integration",
  "dependencies": [],
  "codeowners": [],
  "requirements": ["pyserial-asyncio==0.6"],
  "usb": [
    {
      "vid": "0403",
      "pid": "6001",
      "description": "*Edisio*"
    },
    {
      "vid": "067B",
      "pid": "2303"
    }
  ],
  "iot_class": "local_push"
}
```

- [ ] **Step 2: Write `const.py`**

```python
DOMAIN = "edisio"
CONF_SERIAL_PORT = "serial_port"
CONF_ACTIVE_BUTTONS = "active_buttons"
DEFAULT_ACTIVE_BUTTONS = 5
```

- [ ] **Step 3: Commit**

```bash
git add custom_components/edisio/manifest.json custom_components/edisio/const.py
git commit -m "chore: add manifest and constants for edisio integration"
```

### Task 3: Config Flow and Options Flow (EBP8-B Setup)

**Files:**
- Create: `custom_components/edisio/config_flow.py`
- Create: `custom_components/edisio/strings.json`

- [ ] **Step 1: Write the translations (`strings.json`)**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Edisio USB Serial connection",
        "data": {
          "serial_port": "Serial Port (e.g. /dev/ttyUSB0)"
        }
      },
      "usb": {
        "title": "Discovered Edisio USB dongle",
        "description": "Do you want to configure the Edisio integration with this USB dongle at {serial_port}?"
      }
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "EBP8-B Switch Configuration",
        "data": {
          "active_buttons": "Number of active buttons (1-5)"
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write `config_flow.py` implementation**

```python
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_SERIAL_PORT, CONF_ACTIVE_BUTTONS, DEFAULT_ACTIVE_BUTTONS

class EdisioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Edisio Dongle", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_SERIAL_PORT): str}),
        )

    async def async_step_usb(self, discovery_info):
        self._serial_port = discovery_info.device
        await self.async_set_unique_id(self._serial_port)
        self._abort_if_unique_id_configured()
        
        return self.async_show_form(
            step_id="usb",
            description_placeholders={"serial_port": self._serial_port}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EdisioOptionsFlowHandler(config_entry)

class EdisioOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
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
```

- [ ] **Step 3: Commit**

```bash
git add custom_components/edisio/config_flow.py custom_components/edisio/strings.json
git commit -m "feat: add config flow and options flow"
```

### Task 4: Home Assistant Integration Init (`__init__.py`)

**Files:**
- Modify: `custom_components/edisio/__init__.py`

- [ ] **Step 1: Write integration setup**

```python
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_SERIAL_PORT

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    port = entry.data.get(CONF_SERIAL_PORT)
    # Edisio Hub logic would start serial reading here
    hass.data[DOMAIN][entry.entry_id] = {"port": port}
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/edisio/__init__.py
git commit -m "feat: setup integration init lifecycle"
```
