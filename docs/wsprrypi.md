# Use with WsprryPi

WsprryPi manages the Pico's settings, native schedules, status, pairing, and recovery. The Pico executes its own saved schedules and owns RF timing. A Pi executes its own schedule through its local transmitter backend; it does not dispatch transmissions to another device.

## Set up management

Open **Setup → Fleet** in WsprryPi. Select the intended device by its full identity and choose **Manage settings**. A display name or profile label alone is not device identity. Saving a connection profile does not enable a schedule.

USB management provides configuration and qualified controller time without Wi-Fi. Engineering HTTPS uses the configured certificates and server identity. Consumer Wi-Fi requires its explicit authenticated login. Each connection preserves its own device, boot, profile, and revision checks. An offline or changed target remains unavailable until a fresh verified connection is established.

Review the schedule on the selected Pico before enabling it. The Pico continues eligible occurrences after the managing browser or Pi disconnects while its clock remains qualified. It skips missed occurrences and those for which its clock is unready.

## Ownership and schedules

The Pico's native scheduler reserves its own transmitter. Management access does not grant execution ownership. **Stop native schedules** disables saved WSPR and keyed-message recurrence and confirms inactive, unowned output. A refused or lost reply requires **Read stop status**; connection loss alone is not stop evidence. Local button and Console STOP remain separate safety controls. See [stop and recovery](operate.md#status-stop-and-connection-loss).

## Standalone installer on a WsprryPi host

Use the [settings-preserving USB installer](install.md#preserve-settings-during-an-update). First stop native schedules and confirm inactive, unowned output. Give the installer exclusive access to the selected physical USB device and keep the same Pico connected through verification. Follow the installer's same-board recovery procedure if an outcome is uncertain.

For device-side operation, use this manual's [connections](connect.md), [configuration](configure.md), [output limits](reference/output.md), and [maintenance and recovery](maintain.md).
