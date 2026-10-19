# Troubleshoot

| Symptom | Check and recovery |
| --- | --- |
| Setup Wi-Fi disappears | Each window lasts ten minutes. Deliberately request another with the configured button, or use USB. Read saved state before repeating setup. |
| `.local` does not open | Use the current router-assigned IP, verify device ID, and check for duplicate names or client isolation. |
| Login fails | Use the Wi-Fi password saved on this Pico. Reconnect after a password/profile change. Check the device identity before entering it. |
| All logins occupied | Use **Recover an occupied login**, inspect entries and explicitly retire the selected one with the current saved Wi-Fi password. A shared password does not identify the owner. |
| Save outcome uncertain | Reconnect, **Read saved settings and keep draft**, compare and explicitly review. For setup, use **Check saved result**. Do not automatically repeat a mutation. |
| Schedule does not transmit | Confirm enabled schedule, saved base frequency, complete station, UTC readiness, no expiry, ownership, active pins and no restart/STOP/inhibit. Missed slots are not replayed. |
| STOP/shutdown remains after saving | Review the saved schedule, leave it disabled unless output is intended, confirm idle/inactive, then explicitly restart. Configuration saves do not clear STOP. |
| Start refused for clock | Check time server/network or controller-time delivery. Allow fresh synchronization; do not use manual PPM to fix UTC. |
| Restart required after reverting a pin/drive edit | The restart latch persists for that boot. Review saved wiring/drive and perform an explicit restart while idle. |
| Foreign owner or busy | Stop and release through the owning controller; reconnecting elsewhere does not take over. |
| Frequency rejected | Check native range, band support, all mark/space frequencies and both host/Pico policy. Experimental consent cannot expand the engine's range. |
| 32-character message refused | The whole compiled job may exceed 512 events or 60 minutes. Reduce repeats, gaps, dot duration or message length. |
| Type 3 shows `<...>` | The receiver may lack callsign hash context. Receive the preceding Type 2; grid/power can decode without a resolved name. |
| USB installer refuses | Check selected serial/port, Pico 2 W confirmation, picotool USB support, idle/unowned state, exact image channel and manifest. Follow its specific refusal. |
| Installer asks for BOOTSEL | Preparation is incomplete. Reconnect that same board and port, then run the printed continuation command. |
| Network drops while output may be running | Treat output as unknown. Use the owner or configured shutdown button and confirm inactive before touching the RF path. |

For reset consequences and useful diagnostic fields, see [Maintain and
recover](maintain.md). For an installation problem, retain the exact transaction
and its private backup until it is resolved.
