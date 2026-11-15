# Home Assistant Edisio Integration

A native, strictly typed Home Assistant integration to manage the Edisio RF protocol via a USB serial dongle (e.g. FTDI or Prolific chipsets).

This integration is explicitly designed to replace legacy implementations (like the RFPlayer integration) by offering direct, latency-free communication with your Edisio switch bases, particularly focusing on the **EBP8 8-button switch base** (EBP8-W white and EBP8-B black are identical apart from the colour).

## Supported Devices

The integration recognises two kinds of Device (*Device model*), told apart by the Model code each Device sends in its packets:

| Device model | Products | Status | Reports |
| --- | --- | --- | --- |
| Wall plate | EBP8-W, EBP8-B | Tested | Button presses (`edisio_button_event`, Button sensors) and Battery |
| Opening sensor | EDS-100 | Tested | Open/Closed and Battery |
| Opening sensor | EOS-200 | **Untested** | Expected to behave like the EDS-100 (same Model code), but no one has confirmed it |

If you own an EOS-200, please try it and report what you see (including reversed Open/Closed states) in a GitHub issue.

## Hardware Requirements

To use this integration, you **must** have the official **Edisio USB PC Dongle (868 MHz)** plugged into your Home Assistant server.
The dongle is built on a Prolific (PL2303, `067b:2303`) USB-to-Serial chipset, which Home Assistant discovers automatically. FTDI (FT232R) chips are deliberately not matched, because the RFPlayer dongle uses one; if your dongle is a different chip, add it manually by serial port.

## Features

- **Direct USB Communication:** Parses the 433/868 MHz raw RF frames natively within Home Assistant.
- **Short & Long Press Support:** Distinguishes between standard clicks and long presses directly from the RF frames. One physical press fires exactly one event: a short press one `short_press`, a hold one `long_press` (no repeats while held).
- **Opening sensors:** shows an Edisio Opening sensor (EDS-100) as Open or Closed, with a Battery level, both restored after a restart. See [Opening sensors](#opening-sensors).
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

> [!NOTE]
> This section describes a Wall plate. For an Opening sensor, see [Opening sensors](#opening-sensors).

Once the Edisio Dongle is configured:
1. Press any physical button on a new Edisio switch board.
2. The integration will automatically intercept the RF signal and trigger a discovery flow.
3. A discovery card will appear on the **Devices & Services** integrations dashboard, titled **Edisio Wall plate `<Radio ID>`**. A Device with a Model code the integration does not know is titled **Edisio unknown Device `<Radio ID>` (Model code `<code>`)** and is added as a Wall plate.
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

- **Add a Device:** enter its Radio ID (8 hex digits, e.g. `0670A248`) without pressing it, choose the **Device model** (Wall plate or Opening sensor), and optionally a name and area. For a Wall plate also choose the Button layout. The Add form always shows the Button layout field (labelled "Wall plate only"); for an Opening sensor it is ignored, so leave it alone.
- **Edit a Device:** change its name, Button layout or area (an Opening sensor has no Button layout, so only its name and area are offered). The Device model cannot be changed. Button sensors for Button numbers no longer in the layout are removed and the others are kept. Tick *Also update entity IDs to match the name* to rename entity IDs too (off by default, so dashboards and scripts keep working). Changing the name replaces any name set on the Home Assistant device page.
- **Remove a Device:** forgets the Device and deletes its sensors. If it is pressed again, a new discovery card is offered.

### Ignoring a Device

To stop being offered a Device you do not want, such as a neighbour's, click **Ignore** on its discovery card. An ignored Device raises no card, gets no sensors and fires no events. Its packets still appear in the debug log.

- **Stop ignoring:** on the Edisio integration page, open the menu and choose **Show ignored**, then **Stop ignoring** on the Device. A new discovery card is offered the next time the Device transmits.
- **Add a Device** with the Radio ID of an ignored Device adds it and stops ignoring it.

## Opening sensors

An Opening sensor (EDS-100; EOS-200 untested) is recognised automatically from its Model code `09`, so you never pick its model on the discovery card.

### Adding a sensor

1. Move the magnet away from or against the sensor, or press its Sensor button.
2. A discovery card **Edisio Opening sensor `<Radio ID>`** appears on the **Devices & Services** dashboard and says it is an Opening sensor.
3. Click **Configure**. The card asks only for an optional name (default `Edisio Opening sensor <Radio ID>`) and an area. There is no Button layout.
4. Submit. You get one device under the Edisio Dongle with an **Open/Closed** sensor and a **Battery** sensor. There are no Button sensors and no `edisio_button_event`.

You can also add a sensor by hand from **Configure** -> **Add a Device**, typing its Radio ID and choosing the Opening sensor model.

### States

- The Open/Closed sensor is **Open** (on) when the magnet is away from the sensor and **Closed** (off) when it is against it. It follows the magnet as soon as it moves.
- Use Home Assistant's own **Show as** option (entity settings) to display it as a door, window or similar; there is no setting in the integration.
- The **Sensor button** (the push button on the sensor) updates the Battery level and nothing else, so testing a sensor never reports a false door movement.
- Both the Open/Closed state and the Battery level are restored after a Home Assistant restart. A sensor shows *unknown* only until it has reported for the first time.

> [!WARNING]
> **Known limit:** the sensor only transmits when the magnet moves. If a door is opened or closed while Home Assistant is down (or the Dongle is unplugged), Home Assistant keeps showing the old state until the next movement. The sensor is never marked unavailable for being quiet: no heartbeat has been observed.

### A sensor configured as a Wall plate

Before this feature, an Opening sensor was offered as a Wall plate. If you configured one that way, it is stored as a Wall plate and the model cannot be changed afterwards. To fix it:

1. Open **Configure** -> **Remove a Device** and remove the Device (this deletes its sensors).
2. Move the magnet or press the Sensor button. A new discovery card is offered, now as an Opening sensor.
3. Configure it as above.

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

Upon discovering a new Device, the integration automatically registers a Battery sensor tied to that Device's Radio ID. The Battery level is updated every time the Device transmits (a Wall plate when a Button is pressed, an Opening sensor when it moves or its Sensor button is pressed) and is restored after a restart.

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
> The blueprint only offers Wall plates (Devices whose model is `EBP8`); Opening sensors are never offered. It now selects model `EBP8` (previously `EBP8-B`). If you imported an earlier copy, re-import it, otherwise your Devices are not offered.

> [!NOTE]
> Automations created from the earlier version of the blueprint (inputs `button_1_*` to `button_5_*` and a typed Device ID) are not migrated. Recreate them from the new blueprint.

## Releasing (maintainers)

Releases are published from tags by `.github/workflows/release.yml`, which fails unless the tag matches `version` in `manifest.json`, runs hassfest, the HACS check and the tests, then creates the GitHub Release the Marketplace installs from.

1. `scripts/release.sh X.Y.Z` opens a PR bumping the manifest version. Merge it once CI is green.
2. `scripts/release.sh X.Y.Z` again tags the merged commit `vX.Y.Z` and pushes the tag (it asks first).
