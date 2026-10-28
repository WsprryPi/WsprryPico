# Device presentation

## Delivered presentation and authority

`device-presentation.js` owns heading, title, stable ID, boot observation and
freshness. Each request captures an epoch; a new request, identity bind, logout
or failure invalidates superseded observations. Consumer public metadata uses an
exact schema/key set and exact current device/boot pair. A different full device
cannot replace a retained target. A new observed consumer boot clears the old
name until fresh readback. Authenticated names supersede unsolicited public metadata; a late public failure cannot mark a newer authenticated observation stale. An explicit fresh public-read observation after logout can replace that state only for the same bound device and boot, and is labelled Public observation.

The one H1 stays above both views. About this Pico / Diagnostics is last in Station Control, after Saved settings and recovery. Opening/selecting text requires no login, permission,
clipboard API or request. Stable ID is all 32 lowercase hexadecimal characters;
boot ID is separately labelled. Native focus, 44 px summary targets, light palette
and wrapping are retained. Heading/Diagnostics are ordinary text, without polling
live announcements. Explicit recovery/retirement confirmations keep their IDs.

Save and Restart stay separate. A consumer save ends its session; the old active
name remains last-confirmed, with the accepted saved name secondary and pending.
Engineering saves retain their authenticated readback. Restart monitoring never
promotes a new name without same-device/new-boot readback. Receipt, wrong-device,
draft, read/review, area/history and one-shot restart behavior stay intact.
Discovery conflicts do not rename or erase the configured active name. Identity rendering introduces no API,
protocol, carrier, session crypto, profile, RF, scheduler or JobService authority
change; there is no new polling or transport task.

The lock button is a sibling of the mutable hostname text node, so observation updates cannot erase it or include icon text in the title. Its native action label and visually hidden state describe browser access without a repeated helper line. Certificate-authenticated engineering pages explain their browser-managed access rather than pretending to revoke a client certificate. See [browser access and sections](browser-pages.md#browser-access).
