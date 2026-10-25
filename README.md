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

## Installation

### Method 1: HACS (Recommended)

To install via HACS as a custom repository:
1. Open **HACS** in your Home Assistant dashboard.
2. Go to **Integrations** -> Top right menu -> **Custom repositories**.
3. In the **Repository** field, paste: `https://github.com/SebZbp/ha-edisio-integration`
4. Select **Integration** as the Category and click **Add**.
5. Find the **Edisio Smart Home** integration card, click **Download**, and select the latest version.
6. Restart Home Assistant.

### Method 2: Manual

1. Download or clone this repository.
2. Copy the `custom_components/edisio` folder into your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

Once installed and Home Assistant has restarted:
1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Edisio**.
3. If your Edisio USB dongle is plugged in, Home Assistant should automatically discover it. Otherwise, manually enter your serial port (e.g., `/dev/ttyUSB0`).
4. Click submit to create the **Edisio Dongle** device.

## Device Discovery & Configuration

Once the Edisio Dongle is configured:
1. Press any physical button on a new Edisio switch board.
2. The integration will automatically intercept the RF signal and trigger a discovery flow.
3. A discovery notification card will appear on the **Devices & Services** integrations dashboard: **Edisio Device `<device_id>` Discovered**.
4. Click **Configure** on the discovery card.
5. You will be prompted to select the number of active buttons on your switch board (Config 1 to Config 5):
   * **Config 1:** 1 button (Button number 05)
   * **Config 2:** 2 buttons (Button numbers 04 & 06)
   * **Config 3:** 3 buttons (Button numbers 02, 07 & 08)
   * **Config 4:** 4 buttons (Button numbers 01, 03, 07 & 08)
   * **Config 5:** 5 buttons (Button numbers 01, 03, 05, 07 & 08)
6. Click submit. The device is created and nested under the parent **Edisio Dongle** device, generating a battery sensor and one button sensor per Button number (e.g. `Button 01`, `Button 03`, `Button 05`, `Button 07`, `Button 08` for Config 5).

## Button Sensor States

Each button sensor is named `Button <Button number>`, using the same two-digit Button number the switch sends and that appears in the `button` field of `edisio_button_event` (e.g. the sensor `Button 05` reacts to events with `button: "05"`). Unique IDs are `<Radio ID>_button_<Button number>`.

> [!NOTE]
> Upgrading from an earlier version renames existing button sensors (e.g. `Button 2` becomes `Button 03`) but keeps their entity IDs, history and customisations. Newly created sensors get entity IDs ending in `_button_<Button number>`.

Button sensors represent the state of each button:
- `normal` (Idle)
- `short-press` (Transitions on toggle/short action)
- `long-press` (Transitions on up/down actions)

The state automatically resets back to `normal` after 1 second.

## Usage: Automations

Whenever you press a button on an Edisio switch, this integration fires a native `edisio_button_event` onto the Home Assistant event bus. You can trigger manual automations off this event.

The trigger payload looks like this:

```yaml
trigger:
  - platform: event
    event_type: edisio_button_event
    event_data:
      device_id: "06709603"
      button: "05"
      type: "short_press" # Can be 'short_press' or 'long_press'
```

## Diagnostic Sensors

Upon discovering a new switch, the integration automatically registers a Battery sensor tied to that Device ID. The battery level is updated dynamically every time the switch is pressed.

---

## Blueprints (Alpha Version)

> [!WARNING]
> The blueprint support is currently in **Alpha**. It is functional but undergoing testing.

To make migration from the old `RFPlayer` integration painless, we've included an Automation Blueprint.

### Using the Blueprint
1. Copy the blueprint from `blueprints/automation/edisio/ebp8b_controller.yaml` to your Home Assistant `blueprints/automation/edisio/` folder (or import it).
2. Go to **Settings** -> **Automations & Blueprints** -> **Blueprints**.
3. Create a new automation from the **Edisio EBP8-B Switch Controller** blueprint.
4. Pick your switch from the list of Edisio devices (e.g. "BP Cuisine"). The blueprint reads its Radio ID from the device, so there is nothing to type.
5. Open the section for each Button number your switch has and drop in the actions you want for short and long presses. Leave the other Buttons empty.

The blueprint requires Home Assistant 2024.6 or later (collapsible input sections).

#### Button numbers per layout

A switch sends Button numbers `01` to `08`; which ones depends on its Button layout:

| Button layout | Button numbers sent |
| --- | --- |
| 1 Button | `05` |
| 2 Buttons | `04 06` |
| 3 Buttons | `02 07 08` |
| 4 Buttons | `01 03 07 08` |
| 5 Buttons | `01 03 05 07 08` |

> [!NOTE]
> Automations created from the earlier version of the blueprint (inputs `button_1_*` to `button_5_*` and a typed Device ID) are not migrated. Recreate them from the new blueprint.
