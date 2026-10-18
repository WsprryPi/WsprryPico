# Device presentation

## Delivered presentation and authority

`device-presentation.js` owns heading, title, stable ID, boot observation and
freshness. Each request captures an epoch; a new request, identity bind, logout
or failure invalidates superseded observations. Consumer public metadata uses an
exact schema/key set and exact current device/boot pair. A different full device
cannot replace a retained target. A new observed consumer boot clears the old
name until fresh readback. Authenticated names supersede public metadata; a late
public failure cannot mark a newer authenticated observation stale.

The one H1 and native About this Pico / Diagnostics disclosure are shared outside
both area-hidden containers. Opening/selecting text requires no login, permission,
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
