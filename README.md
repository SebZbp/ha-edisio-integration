# Home Assistant Edisio Integration

A native, strictly typed Home Assistant integration to manage the Edisio RF protocol via a USB serial dongle (e.g. FTDI or Prolific chipsets).

This integration is explicitly designed to replace legacy implementations (like the RFPlayer integration) by offering direct, latency-free communication with your Edisio switch bases, particularly focusing on the **EBP8-B 8-button switch**.

## Hardware Requirements

To use this integration, you **must** have the official **Edisio USB PC Dongle (868 MHz)** plugged into your Home Assistant server.
The dongle is built using standard FTDI (FT232R) or Prolific (PL2303) USB-to-Serial chipsets, which are automatically discovered by Home Assistant.

## Features

- **Direct USB Communication:** Parses the 433/868 MHz raw RF frames natively within Home Assistant.
- **Short & Long Press Support:** Distinguishes between standard clicks and long presses (dimming) directly from the RF frames.
- **Battery Diagnostics:** Automatically creates battery sensors for discovered Edisio switches, keeping track of power levels dynamically.
- **Blueprint Migration:** Includes a built-in automation Blueprint to smoothly map legacy RFPlayer logic onto the new `edisio_button_event` architecture.

## Installation

### Method 1: HACS (Recommended)
*(Assuming you add this repository to HACS as a custom repository)*
1. Open HACS in Home Assistant.
2. Go to **Integrations** -> Top right menu -> **Custom repositories**.
3. Add `https://github.com/SebZbp/ha-edisio-integration` as an Integration.
4. Restart Home Assistant.

### Method 2: Manual
1. Download or clone this repository.
2. Copy the `custom_components/edisio` folder into your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

Once installed and Home Assistant has restarted:
1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Edisio**.
3. If your Edisio USB dongle is plugged in, Home Assistant should automatically discover it. Otherwise, manually enter your serial port (e.g., `/dev/ttyUSB0`).
4. Select the number of physical buttons active on your switch via the Options flow.

## Usage: Automations & Blueprints

Whenever you press a button on an Edisio switch, this integration fires a native `edisio_button_event` onto the Home Assistant event bus.

### The Easy Way: Using the Blueprint
To make migration from the old `RFPlayer` integration painless, we've included an Automation Blueprint.

1. Copy the blueprint from `blueprints/automation/edisio/ebp8b_controller.yaml` to your Home Assistant `blueprints/automation/edisio/` folder (or import it).
2. Go to **Settings** -> **Automations & Blueprints** -> **Blueprints**.
3. Create a new automation from the **Edisio EBP8-B Switch Controller** blueprint.
4. Select your Device ID (e.g., `00000001`).
5. Use the visual editor to drop in the exact actions you want for short and long presses on each button!

### The Manual Way: Listening to Events
If you prefer writing manual automations, you can trigger off the raw event. The payload looks like this:

```yaml
trigger:
  - platform: event
    event_type: edisio_button_event
    event_data:
      device_id: "00000001"
      button: "01"
      type: "short_press" # Can be 'short_press' or 'long_press'
```

## Diagnostic Sensors

Upon discovering a new switch, the integration will automatically register a Battery sensor tied to that Device ID. The battery level will be updated dynamically every time the switch is pressed.
