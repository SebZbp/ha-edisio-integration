# Home Assistant Edisio Integration

A native, strictly typed Home Assistant integration to manage the Edisio RF protocol via a USB serial dongle (e.g. FTDI or Prolific chipsets).

This integration is explicitly designed to replace legacy implementations (like the RFPlayer integration) by offering direct, latency-free communication with your Edisio switch bases, particularly focusing on the **EBP8 8-button switch base** (EBP8-W white and EBP8-B black are identical apart from the colour).

## Hardware Requirements

To use this integration, you **must** have the official **Edisio USB PC Dongle (868 MHz)** plugged into your Home Assistant server.
The dongle is built on a Prolific (PL2303, `067b:2303`) USB-to-Serial chipset, which Home Assistant discovers automatically. FTDI (FT232R) chips are deliberately not matched, because the RFPlayer dongle uses one; if your dongle is a different chip, add it manually by serial port.

## Features

- **Direct USB Communication:** Parses the 433/868 MHz raw RF frames natively within Home Assistant.
- **Short & Long Press Support:** Distinguishes between standard clicks and long presses directly from the RF frames. One physical press fires exactly one event: a short press one `short_press`, a hold one `long_press` (no repeats while held).
- **Device management:** Add, edit and remove Devices from the integration's options, without waiting for a discovery card.
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

The serial port is stored as its stable `/dev/serial/by-id/...` path when one exists, so it survives reboots and other USB serial devices being plugged in. Entries created by earlier versions are converted automatically on upgrade; this cannot be undone by downgrading.

## Device Discovery & Configuration

Once the Edisio Dongle is configured:
1. Press any physical button on a new Edisio switch board.
2. The integration will automatically intercept the RF signal and trigger a discovery flow.
3. A discovery notification card will appear on the **Devices & Services** integrations dashboard: **Edisio Device `<Radio ID>` Discovered**.
4. Click **Configure** on the discovery card. It shows the Radio ID and the Button number that was pressed.
5. Select the Device's Button layout (number of active Buttons, 1 to 5), and optionally give it a name (default `Edisio EBP8-B <Radio ID>`) and an area:
   * **1 Button:** Button number 05
   * **2 Buttons:** Button numbers 04 & 06
   * **3 Buttons:** Button numbers 02, 07 & 08
   * **4 Buttons:** Button numbers 01, 03, 07 & 08
   * **5 Buttons:** Button numbers 01, 03, 05, 07 & 08
6. Click submit. The device is created and nested under the parent **Edisio Dongle** device, generating a battery sensor and one button sensor per Button number (e.g. `Button 01`, `Button 03`, `Button 05`, `Button 07`, `Button 08` for the 5-Button layout).

## Managing Devices

Open **Settings** -> **Devices & Services** -> **Edisio** -> **Configure** to manage Devices:

- **Add a Device:** enter its Radio ID (8 hex digits, e.g. `0670A248`) without pressing it, then choose the Button layout and optionally a name and area.
- **Edit a Device:** change its name, Button layout or area. Button sensors for Button numbers no longer in the layout are removed and the others are kept. Tick *Also update entity IDs to match the name* to rename entity IDs too (off by default, so dashboards and scripts keep working). Changing the name replaces any name set on the Home Assistant device page.
- **Remove a Device:** forgets the Device and deletes its sensors. If it is pressed again, a new discovery card is offered.

## Button Sensor States

Each button sensor is named `Button <Button number>`, using the same two-digit Button number the Device sends and that appears in the `button` field of `edisio_button_event` (e.g. the sensor `Button 05` reacts to events with `button: "05"`). Unique IDs are `<Radio ID>_button_<Button number>`.

> [!NOTE]
> Upgrading from an earlier version renames existing button sensors (e.g. `Button 2` becomes `Button 03`) but keeps their entity IDs, history and customisations. Newly created sensors get entity IDs ending in `_button_<Button number>`.

Button sensors represent the state of each button:
- `normal` (Idle)
- `short-press` (Transitions on toggle/short action)
- `long-press` (Transitions on up/down actions)

The state automatically resets back to `normal` after 1 second.

## Usage: Automations

Whenever you press a button on an Edisio switch, this integration fires a native `edisio_button_event` onto the Home Assistant event bus. You can trigger manual automations off this event.

The trigger payload looks like this. `device_id` holds the Device's Radio ID (the 8-hex-digit identifier it sends in every packet), not a Home Assistant device ID:

```yaml
trigger:
  - platform: event
    event_type: edisio_button_event
    event_data:
      device_id: "06709603" # the Device's Radio ID, not a Home Assistant device ID
      button: "05"
      type: "short_press" # Can be 'short_press' or 'long_press'
```

## Diagnostic Sensors

Upon discovering a new switch, the integration automatically registers a Battery sensor tied to that Device ID. The battery level is updated dynamically every time the switch is pressed.

The Edisio Dongle device has a **Connection** sensor: it turns off when the Dongle is unplugged or its serial port fails, and back on once the integration has reopened the port. Reopening is automatic, retrying every 1 second at first and backing off to once a minute, so no reload is needed. If the Dongle is already missing when Home Assistant starts, Home Assistant keeps retrying the integration's setup and the Connection sensor stays unavailable until the port opens. Automations can trigger on this sensor to warn you of an outage; button presses made during one are lost.

---

## Blueprints (Alpha Version)

> [!WARNING]
> The blueprint support is currently in **Alpha**. It is functional but undergoing testing.

To make migration from the old `RFPlayer` integration painless, we've included an Automation Blueprint.

### Using the Blueprint
1. Copy the blueprint from `blueprints/automation/edisio/ebp8b_controller.yaml` to your Home Assistant `blueprints/automation/edisio/` folder (or import it).
2. Go to **Settings** -> **Automations & Blueprints** -> **Blueprints**.
3. Create a new automation from the **Edisio EBP8-B Switch Controller** blueprint (it works with EBP8-W and EBP8-B bases).
4. Pick your Device from the list of Edisio Devices (e.g. "BP Cuisine"); the Dongle is not offered. The blueprint reads its Radio ID from the Device, so there is nothing to type.
5. Open the section for each Button number your Device has and drop in the actions you want for short and long presses. Leave the other Buttons empty.

The blueprint requires Home Assistant 2024.6 or later (collapsible input sections).

#### Button numbers per layout

A Device sends Button numbers `01` to `08`; which ones depends on its Button layout:

| Button layout | Button numbers sent |
| --- | --- |
| 1 Button | `05` |
| 2 Buttons | `04 06` |
| 3 Buttons | `02 07 08` |
| 4 Buttons | `01 03 07 08` |
| 5 Buttons | `01 03 05 07 08` |

> [!NOTE]
> The blueprint now selects Devices whose model is `EBP8` (previously `EBP8-B`). If you imported an earlier copy, re-import it, otherwise your Devices are not offered.

> [!NOTE]
> Automations created from the earlier version of the blueprint (inputs `button_1_*` to `button_5_*` and a typed Device ID) are not migrated. Recreate them from the new blueprint.
