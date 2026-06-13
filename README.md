# Home Assistant Edisio Integration

A native, strictly typed Home Assistant integration to manage the Edisio RF protocol via a USB serial dongle (e.g. FTDI or Prolific chipsets).

This integration is explicitly designed to replace legacy implementations (like the RFPlayer integration) by offering direct, latency-free communication with your Edisio switch bases, particularly focusing on the **EBP8-B 8-button switch**.

## Hardware Requirements

To use this integration, you **must** have the official **Edisio USB PC Dongle (868 MHz)** plugged into your Home Assistant server.
The dongle is built using standard FTDI (FT232R) or Prolific (PL2303) USB-to-Serial chipsets, which are automatically discovered by Home Assistant.

## Features

- **Direct USB Communication:** Parses the 433/868 MHz raw RF frames natively within Home Assistant.
- **Dynamic Device Configuration:** Discovers new switches automatically and prompts configuration for active buttons.
- **Button Entity States:** Exposes clean, sequential button sensors (`Button 1`, `Button 2`, etc.) transitioning between press states with a 1-second auto-reset.
- **Battery Diagnostics:** Automatically creates battery sensors for discovered Edisio switches, keeping track of power levels dynamically.
- **Blueprint Migration:** Includes a built-in automation Blueprint to smoothly map legacy RFPlayer logic onto the new `edisio_button_event` architecture.

## Installation

### Method 1: HACS (Recommended)

To install via HACS as a custom repository:
1. Open **HACS** in your Home Assistant dashboard.
2. Click on the three dots in the top-right corner and select **Custom repositories**.
3. In the **Repository** field, paste: `https://github.com/SebZbp/ha-edisio-integration`
4. Select **Integration** as the Category and click **Add**.
5. Find the **Edisio Smart Home** integration card, click **Download**, and select the latest version.
6. Restart Home Assistant.

### Method 2: Manual

1. Download or clone this repository.
2. Copy the `custom_components/edisio` folder into your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration & Adding New Devices

### 1. Configure the USB Dongle
1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Edisio**.
3. If your Edisio USB dongle is plugged in, Home Assistant should automatically discover it. Otherwise, manually enter your serial port (e.g., `/dev/ttyUSB0`).
4. Click submit to create the **Edisio Dongle** device.

### 2. Add Edisio Switches (Devices)
New devices are registered dynamically:
1. Press any button on the physical Edisio switch board.
2. The integration will intercept the incoming RF packet and trigger a configuration flow.
3. A discovery notification card will appear on the **Devices & Services** integrations dashboard: **Edisio Device `<device_id>` Discovered**.
4. Click **Configure** on the card.
5. Select the number of physically active buttons on your switch board (Config 1 to Config 5).
6. Click submit. The device will be registered and nested hierarchically under the parent **Edisio Dongle** device.

## Button Sensor States

For each configured switch, the integration creates one **Battery** sensor and the corresponding number of sequential **Button** sensors (`Button 1`, `Button 2`, etc.):
*   **Idle State:** `normal`
*   **Click State:** `short-press` (Transitions on toggle/short action)
*   **Hold State:** `long-press` (Transitions on up/down packet actions)

Button sensors automatically reset their state back to `normal` **1 second** after the last button press.

## Usage: Automations & Blueprints

Whenever you press a button on an Edisio switch, this integration fires a native `edisio_button_event` onto the Home Assistant event bus in addition to updating the button sensor state.

### The Easy Way: Using the Blueprint
To make migration from the old `RFPlayer` integration painless, we've included an Automation Blueprint.

1. Copy the blueprint from `blueprints/automation/edisio/ebp8b_controller.yaml` to your Home Assistant `blueprints/automation/edisio/` folder (or import it).
2. Go to **Settings** -> **Automations & Blueprints** -> **Blueprints**.
3. Create a new automation from the **Edisio EBP8-B Switch Controller** blueprint.
4. Select your Device ID (e.g., `06709603`).
5. Use the visual editor to drop in the exact actions you want for short and long presses on each button!

### The Manual Way: Listening to Events
If you prefer writing manual automations, you can trigger off the raw event. The payload looks like this:

```yaml
trigger:
  - platform: event
    event_type: edisio_button_event
    event_data:
      device_id: "06709603"
      button: "05"
      type: "short_press" # Can be 'short_press' or 'long_press'
```
