# KilnAid for Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zander8807&repository=home-assistant-kilnaid&category=integration)

An experimental, read-only Home Assistant custom integration for L&L and other
kilns using a Bartlett Genesis controller connected to the KilnAid cloud.

## Features

- UI-based setup with your KilnAid email and password
- Automatic token acquisition and reauthentication
- One shared cloud poll every 2 minutes
- Kiln status, program, segment, setpoint, firing time, and hold time
- Chamber and per-zone temperatures
- Firing, error, and cloud-connectivity binary sensors
- Optional controller, current, and voltage diagnostic sensors when available
- Persistent firing records and an optional companion history card

## Firing archive (v0.2.0)

Each kiln's observed firings are saved independently of Recorder in
`.storage/kilnaid.firings.<config-entry-id>`. Records include program, first
observed firing time, observed heating end and outcome, recorded peak, temperature
unit, stage/status samples, partial-start and gap flags. Cooling readings continue
for up to 48 hours after heating ends or until another firing starts.
Records are retained without automatic expiry; include the Home Assistant config
directory in backups. Disk usage grows with recorded firings. These are local
records, not a download of the controller's complete historical firing log.

On first setup after upgrading, available Recorder history from the past 30 days
is imported once. This cannot recover already-purged data. Subsequent cloud reports
are saved atomically as they arrive (normally every two minutes). Duplicate,
out-of-order and over-15-minute-old cloud reports are ignored.

An observed idle-to-firing transition captures a start within the polling interval.
A recording is marked **partial** if its first observation is already firing or a
gap of more than 15 minutes precedes the start. Missing samples do not themselves
end a firing. Gaps during a firing are flagged separately. A changed firing counter
plus reset elapsed clock can identify a missed firing boundary. Entire firings
while HA or the cloud connection is down cannot reliably be recovered. End times
are observed transitions, not guaranteed exact controller times. A firing's
`outcome` may be Complete, Idle, Error, Stopped or Cooling; stopping is not assumed
to mean successful completion.

### Companion dashboard card

Install **ApexCharts Card** through HACS and add its resource as usual. Add this
JavaScript module under dashboard resources:

```text
/kilnaid/kiln-history-card.js?v=0.2.0
```

The integration serves the bundled card automatically. No separate file copy is
needed. Use your own KilnAid **status** entity:

```yaml
type: custom:kilnaid-history-card
entity: sensor.my_kiln_status
```

The card defaults to the newest firing, offers an archive selector, marks heating
end and shows recorded cooling temperatures. It refreshes once per minute while
mounted, regardless of the kiln's current online state. The archive must be
loaded in Home Assistant; it remains accessible during normal cloud poll failures.

For an optional Bubble Card v3.2+ pop-up, use the standalone format:

```yaml
type: custom:bubble-card
card_type: pop-up
hash: '#kiln-history'
name: Kiln history
button_type: name
cards:
  - type: custom:kilnaid-history-card
    entity: sensor.my_kiln_status
    popup_hash: '#kiln-history'
```

Point a dashboard card's navigation tap action at `#kiln-history`. Setting
`popup_hash` pauses archive requests while the pop-up is closed. Bubble Card is
optional; ApexCharts is only needed to draw the graph.

### Archive API

Authenticated WebSocket command `kilnaid/firings` accepts `entity_id` (a KilnAid
status sensor). It returns newest-first `fires` summaries without samples. Add
`firing_id` to retrieve one full record. It checks the user's read permission for
that entity and scopes records to its kiln/config entry. Archive readings are not
published under `/local` or in sensor attributes. This API can also be used to
export records. No deletion endpoint is provided.

The integration does **not** start, stop, or program the kiln. Home Assistant
must not be treated as a kiln safety controller. Follow the kiln manufacturer's
supervision, installation, ventilation, and clearance requirements.

## One-click installation with HACS

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zander8807&repository=home-assistant-kilnaid&category=integration)

1. Select the button above and choose your Home Assistant instance.
2. In HACS, select **Download** and restart Home Assistant when prompted.
3. Return here and select **Add KilnAid**:

[![Open your Home Assistant instance and start setting up KilnAid.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kilnaid)

4. Enter the email and password used by the KilnAid app.

HACS must already be installed in Home Assistant. If it is not, follow the
[official HACS installation guide](https://www.hacs.xyz/docs/use/download/download/).

## Manual installation

1. Copy `custom_components/kilnaid` into the `custom_components` directory in
   your Home Assistant configuration folder.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **KilnAid** and enter the credentials used by the KilnAid app.

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
