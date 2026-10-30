# GPIO drive strength

The selected member's direct RF output supports **2, 4, 8 and 12 mA**, default
**4 mA**. This is nominal electrical RF-pin drive; actual RF power depends on
load and frequency. Reported WSPR power is independent and never adjusted.
Auxiliary pins and Pi local BCM/RP1/Si5351 settings are unaffected.

Read the authenticated selected member's capabilities `gpio_drive` descriptor.
It explicitly identifies the field, legal values, default, units, direct PIO
engine, read/write routes and restart activation. Absence means unavailable;
never infer support from firmware labels or WTP CAPS. The current contract advertises drive support explicitly.

`GET /api/control/v1/gpio-drive` uses `gpio-drive` and returns the target,
`saved`, `boot_active`, `pad_readback` (mA or null), `rf_gp`, `execution_engine`,
`pending_restart`, `application_error` and `storage_healthy`. Null saved means no
complete configuration; boot-active is this boot's validated selection, including
4 for a healthy unconfigured boot. It is not a physical observation. Inhibited
firmware leaves pad readback null. `rf_gp` identifies the boot-active route; the
saved pin remains in `hardware.saved`. RF firmware reports a verified SDK observation
only after its adapter has initialized during ARM, before local scheduled
launch; LOAD alone does not open it. The value is a cached SDK register
verification from that initialization, bound to this boot, not continuous
electrical sensing. Errors remain explicit.

PUT the same route with exactly `{contract,schema,target,gpio_drive_ma}`, with `contract:"Wsprry-Control/1"`, and current
If-Match. It uses the existing idle/unowned/inactive/nonfaulted admission and
one validated Config journal commit. Loaded/armed/running/faulted states refuse.
Saving does not program the pad. An actual change latches hardware restart and
output inhibition for this boot, including A/B/A. Use the existing explicit
restart. A lost reply is unknown: read authoritative state and review before
another explicit save. No automatic retry or restart is performed.

## Current control model

The stable `gpio-drive` resource belongs to `Wsprry-Control/1`. Application,
hardware and progress expose one complete current representation. Saved-drive
drafts use the current progress resource and explicit drive application; no
historical descriptor or route is selected. GPIO values remain 2/4/8/12 mA,
with independent saved, boot-active and cached pad observations.
