# Home Assistant Edisio Integration Design

## Overview
A native Home Assistant integration for the Edisio RF protocol, based on the protocol logic from the Jeedom Edisio plugin. The initial focus is specifically on supporting the Edisio 8-button switch base (EBP8-B) and USB dongle connectivity, with a decoupled protocol parsing layer.

## Architecture & Project Structure
The project will be built within the `ha-edisio-integration/` directory and is split into two logical layers:

1. **Protocol Layer (`custom_components/edisio/edisio_api.py`)**
   - A decoupled, asynchronous Python library using `pyserial-asyncio`.
   - Manages the async serial connection to the Edisio USB dongle.
   - Decodes raw hexadecimal byte frames from the serial buffer.
   - Emits callbacks with structured data when valid packets are received.

2. **Home Assistant Integration Layer (`custom_components/edisio/`)**
   - Standard Home Assistant custom component architecture.
   - `manifest.json`: Defines the integration and includes USB discovery parameters for FTDI/Prolific chipsets.
   - `config_flow.py`: Manages the setup UI. Supports automatic USB discovery, manual serial port entry, and dynamic device-specific discovery flows for incoming EBP8-B devices.
   - `__init__.py`: Manages the lifecycle of the integration, the `edisio_api` connection, and thread-safe scheduling of events/discovery flows onto the event loop.

## Scope: EBP8-B Switch Base
The initial implementation prioritizes the EBP8-B switch.

- **Configuration:** When a new EBP8-B switch board is dynamically detected on the RF serial interface, a discovery config flow is initiated in Home Assistant. This prompts the user with a form to specify the number of physically active buttons on that board (1, 2, 3, 4, or 5). Until configured, the device is not created, and button events from it are ignored. The configuration is stored under `devices` mapping in the config entry options. The cogwheel options flow is reserved for future non-device configuration.
- **Events:** The integration will map short and long presses to native Home Assistant device triggers (`edisio_button_event`). The event payload will contain the `device_id`, `button` number, and press `type` (`short_press` or `long_press`).
- **Sensors:** The integration will expose diagnostic sensor entities for each paired switch board:
  - **Battery Voltage:** Extracted and decoded from the protocol.
  - **Signal Power (RSSI):** If exposed by the raw RF serial data.

## Device Registry & Hierarchy
- **Edisio Dongle Device:** A master device representing the USB dongle itself is created in the device registry under the config entry.
- **EBP8-B Switches:** Each configured EBP8-B switch is registered in the device registry with `"via_device"` pointing to the "Edisio Dongle" device, establishing a clean device hierarchy.

## Device Discovery (Inclusion Mode)
To prevent interference from neighboring Edisio networks, the integration will filter out packets from unknown devices by default.
- A toggle switch (`switch.edisio_inclusion_mode`) or service will be provided to temporarily allow new devices to be paired.

## Data Flow
- **Incoming:** `Serial Port` -> `pyserial-asyncio Reader` -> `edisio_api (Decoder)` -> `HA Coordinator/Hub Callback` -> `Main Loop scheduling (call_soon_threadsafe)` -> `Check if configured (Options) -> If configured: Fire Event / Update Diagnostic Sensor; If new: Trigger Discovery Flow`
- **Outgoing (Future Proofing):** `HA UI` -> `HA Coordinator/Hub` -> `edisio_api (Encoder)` -> `pyserial-asyncio Writer` -> `Serial Port`

## Error Handling
- **Reconnection:** If the USB dongle is removed or the serial connection is lost, `SerialException` will be caught. The integration will enter a background retry loop and mark associated entities as `unavailable` until the connection is restored.
- **Protocol Errors:** Malformed 433/868 MHz packets will be logged to the `debug` level and gracefully discarded without halting the event loop.

## Migration & RFPlayer Coexistence
- **Coexistence:** The new Edisio integration will use its own dedicated USB dongle (or share via a serial multiplexer if applicable, though a dedicated Edisio dongle is recommended). It will operate independently of the RFPlayer integration, allowing both to run simultaneously during the migration period.
- **Migration Helpers:** 
  - To ease the transition for dozens of EBP8-B switches, the integration will document the exact mapping between RFPlayer entities and the new `edisio_button_event` triggers.
  - We will provide a Home Assistant Blueprint that can "bridge" the new integration's events to the old RFPlayer format, allowing existing automations to continue working without modification until they are natively migrated.

## Testing
- Unit tests will mock the serial byte streams to verify that `edisio_api.py` correctly translates raw hex packets into the expected EBP8-B button numbers, press types, and battery levels.
