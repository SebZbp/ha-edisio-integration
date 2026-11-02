<!-- DRAFT reply for GitHub issue #8. NOT posted; the owner decides when to post. -->

Thanks for the request, and for the Radio ID info.

Opening sensor support is added in **v1.4.0**:

- The **EDS-100** is supported and tested. It shows up as one device with an **Open/Closed** sensor and a **Battery** sensor.
- The **EOS-200** should work the same way (it is expected to send the same Model code), but it is **untested**. If you have one, please try it and tell us what you see, in particular whether Open and Closed are the right way round.

How to add it:

1. Install v1.4.0 and restart Home Assistant.
2. Move the magnet or press the Sensor button on the sensor.
3. A discovery card appears under **Settings -> Devices & Services**. Click **Configure**, then optionally name it and pick an area. (You can also add it by hand from **Configure -> Add a Device** with its Radio ID and the Opening sensor model.)
4. Use HA's **Show as** option on the entity to display it as a door or window.

Good to know:

- The sensor never fires `edisio_button_event`; automate on its Open/Closed state.
- State and battery are restored after a restart, but a door moved while HA is down shows the old state until the next movement.
- If you already configured the sensor as a Wall plate, remove it under **Configure -> Remove a Device**, then move the magnet again to get a new card.

See the README ("Opening sensors") for details.
