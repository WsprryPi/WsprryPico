# Use with WsprryPi

WsprryPi manages the Pico's settings, native schedules, status, pairing, and recovery. The Pico executes its own saved schedules and owns RF timing. A Pi executes its own schedule through its local transmitter backend; it does not dispatch transmissions to another device.

## Set up management

Open **Setup → Fleet** in WsprryPi. Select the intended device by its full identity and choose **Manage settings**. A display name or profile label alone is not device identity. Saving a connection profile does not enable a schedule.

USB management provides configuration and qualified controller time without Wi-Fi. Engineering HTTPS uses the configured certificates and server identity. Consumer Wi-Fi requires its explicit authenticated login. Each connection preserves its own device, boot, profile, and revision checks. An offline or changed target remains unavailable until a fresh verified connection is established.

Review and save the replacement schedule disabled, read it back from the same target, then enable it explicitly. The Pico continues eligible occurrences after the managing browser or Pi disconnects while its clock remains qualified. Missed or clock-unready occurrences are skipped without catch-up transmissions.

## Ownership and schedules

The Pico's native scheduler reserves its own transmitter. Management access does not grant execution ownership. **Stop native schedules** disables saved WSPR and keyed-message recurrence and confirms inactive, unowned output. A refused or lost reply requires **Read stop status**; connection loss alone is not stop evidence. Local button and Console STOP remain separate safety controls. See [stop and recovery](operate.md#status-stop-and-connection-loss).

## Migrating an existing remote-output installation

WTP clients, the WTP transmitter backend, controller-dispatched Fleet recurrence, generic job uploads, and finite browser job submissions are unsupported. Complete migration with WTP-capable software before replacing either peer.

Persistently disable the old controller recurrence, finish or explicitly stop accepted work, confirm inactive and unowned output, and complete retirement for every controller. Offline, stale, or uncertain state remains held. Compare the supported native mode, message, frequency, timing, repetitions, and location rules; unsupported mappings stay disabled. Save and read back the reviewed native schedule disabled before explicitly enabling it. Preserve protected history and retirement receipts for recovery and rollback checks.

The standalone **WSPR dial frequency (Hz)** is a USB dial reference; the Pico places RF tones around dial +1,500 Hz. An old controller RF-center entry is an absolute RF center. These values must not be copied as though they had identical units or semantics.

## Standalone installer on a WsprryPi host

Use the [settings-preserving USB installer](install.md#preserve-settings-during-an-update). First stop native schedules and confirm inactive, unowned output. Give the installer exclusive access to the selected physical USB device; keep its serial and immutable device identity bound through programming and verification. Follow the installer's same-board recovery procedure if an outcome is uncertain. A firmware update does not prove that legacy controller duties were retired.

For device-side operation, use this manual's [connections](connect.md), [configuration](configure.md), [output limits](reference/output.md), and [maintenance and recovery](maintain.md).
