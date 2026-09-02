# KilnAid for Home Assistant

An experimental, read-only Home Assistant custom integration for L&L and other
kilns using a Bartlett Genesis controller connected to the KilnAid cloud.

## Features

- UI-based setup with your KilnAid email and password
- Automatic token acquisition and reauthentication
- One shared cloud poll every 45 seconds
- Kiln status, program, segment, setpoint, firing time, and hold time
- Chamber and per-zone temperatures
- Firing, error, and cloud-connectivity binary sensors
- Optional controller, current, and voltage diagnostic sensors when available

The integration does **not** start, stop, or program the kiln. Home Assistant
must not be treated as a kiln safety controller. Follow the kiln manufacturer's
supervision, installation, ventilation, and clearance requirements.

## Installation

### Manual

1. Copy `custom_components/kilnaid` into the `custom_components` directory in
   your Home Assistant configuration folder.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **KilnAid** and enter the credentials used by the KilnAid app.

### HACS custom repository

1. In HACS, open **Integrations → Custom repositories**.
2. Add this repository as category **Integration**.
3. Install **KilnAid**, restart Home Assistant, and complete the setup above.

## Cloud API notice

KilnAid does not publish an API for third-party integrations. This project uses
the same read endpoints and client headers currently used by the official
KilnAid web application. Bartlett may change them without notice. Your password
is stored in the Home Assistant config entry so the integration can obtain a
fresh opaque token; the token is retained only in memory and is never logged.

This project is not affiliated with or endorsed by Bartlett Instrument or L&L
Kiln Mfg.

## Support

When reporting a problem, enable debug logging for `custom_components.kilnaid`
and remove account email addresses, kiln serial numbers, MAC addresses, and any
authentication values before sharing logs.
