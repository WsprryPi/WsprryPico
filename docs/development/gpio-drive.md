# GPIO drive strength

The selected member's direct RF output supports **2, 4, 8 and 12 mA**, default
**4 mA**. This is nominal electrical RF-pin drive; actual RF power depends on
load and frequency. Reported WSPR power is independent and never adjusted.
Auxiliary pins and Pi local BCM/RP1/Si5351 settings are unaffected.

Read the authenticated selected member's capabilities `gpio_drive` descriptor.
It explicitly identifies the field, legal values, default, units, direct PIO
engine, read/write routes and restart activation. Absence means unavailable;
never infer support from firmware labels or WTP CAPS. Legacy capability objects
continue to list drive unavailable for their old views.

`GET /api/v1/gpio-drive` uses `transmitter-gpio-drive/1` and returns the target,
`saved`, `boot_active`, `pad_readback` (mA or null), `rf_gp`, `execution_engine`,
`pending_restart`, `application_error` and `storage_healthy`. Null saved means no
complete configuration; boot-active is this boot's validated selection, including
4 for a healthy unconfigured boot. It is not a physical observation. Inhibited
firmware leaves pad readback null. `rf_gp` identifies the boot-active route; the
saved pin remains in hardware/2.saved. RF firmware reports a verified SDK observation
only after its adapter has initialized. Errors remain explicit.

PUT the same route with exactly `{schema,target,gpio_drive_ma}` and current
If-Match. It uses the existing idle/unowned/inactive/nonfaulted admission and
one validated Config journal commit. Loaded/armed/running/faulted states refuse.
Saving does not program the pad. An actual change latches hardware restart and
output inhibition for this boot, including A/B/A. Use the existing explicit
restart. A lost reply is unknown: read authoritative state and review before
another explicit save. No automatic retry or restart is performed.

## Compatible extended views

- `GET/PUT /api/v1/config/3` includes effective `gpio_drive_ma`, including 4.
- `POST /api/v1/config/update/3` uses `transmitter-config-update/2` and the
  existing target/mode/config envelope. Merge preserves omission; new explicit
  replacement defaults omitted drive to 4. Initial creation and Console CONFIG
  also default omission to 4. Console export retains canonical default omission;
  STATUS reports its effective saved and boot values explicitly.
- `GET /api/v1/hardware/2` uses `transmitter-hardware/2`, adding the nested
  `gpio_drive` resource; its active digest includes boot drive.
- `GET /api/v1/application/3` uses `transmitter-application/3` and embeds that
  hardware view with existing station/2 and WSPR planning semantics.
- Progress `/2`, update `/2` and apply `/2` use `transmitter-progress/2`.
  `fields.gpio_drive_ma` saves independently of station completeness. Malformed
  supplied drive rejects the whole batch before sibling changes. Explicit
  `application.domain:"drive"` applies only saved drive over a complete Config.
  Radio/all application excludes drive, so older drafts cannot overwrite a newer
  selection accidentally. Draft saving never programs hardware or resumes STOP.

Legacy config/update/application/hardware/progress shapes remain unchanged.
Ordinary legacy writes preserve omitted drive; deliberate replacement defaults it to 4. Legacy progress
apply ignores drive drafts. Supplied unsupported fields reject atomically.
Default legacy serialized bytes are retained; nondefault Config adds one field
in the existing journal. Progress uses saved-progress/2 only when drive exists;
old saved-progress/1 records still load. No address, capacity or recovery rule
changes. Older firmware rejects nondefault Config/new progress records and is
not a supported downgrade path. A deliberate full reset defaults drive; Wi-Fi
and profile overlays preserve it. Do not restore older enabled records after a
new-record decoding failure.

USB uses normal UMP1 bounds, physical identity and response ACKs with Wi-Fi
absent; engineering and Consumer-Radio use existing authentication/session
rules. Pi's protected member/gpio-drive proxy validates the exact descriptor,
selected target, revisions and carrier before forwarding. Older firmware keeps
its other settings usable with drive unavailable. Pico consumer/engineering
and Pi selected-member pages preserve drive drafts and show saved/boot/pad
states beside the control. Save drive progress works without complete station
identity; Apply saved drive requires an applied, complete configuration and
changes only that field. Selecting a value is only a draft.

The RP2350 adapter maps each mA value to named SDK constants, explicitly programs
4 mA too, verifies with the getter, and keeps the PIO output disabled/low during
function changes. Reopen/rearm uses the immutable boot value; mismatch refuses
open/launch. See the [SDK GPIO API](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html#gpio_set_drive_strength)
and the repository-pinned SDK source audit in the execution record.

Software evidence and remaining physical acceptance are tracked in
[P15.15 results](phase15-15-results.md). Nondefault strengths inherit no RF
qualification or power ratio from historical 4 mA campaigns.
