# UDP diagnostic logging

The Pico can send diagnostic events over station Wi-Fi to one explicitly configured IPv4 collector. USB logging has its own enable control, filter and queue. Either sink can operate independently. UDP export does not require a Fleet enrollment or accepted UTC and does not enable a transmit schedule.

**UDP logs are sent in plaintext without authentication. Use a deliberately configured managed network. A successful send does not confirm receipt.** Wi-Fi encryption does not authenticate the collector or protect every network hop.

## Configure export

1. In **Connection and setup Wi-Fi**, open **UDP logging** and choose **Read UDP logging settings**. Verify the Pico device and boot identity. On WsprryPi, select the intended member and use **UDP logging on this Pico**, checking its displayed identity and carrier.
2. Enable export and enter the collector's dotted-decimal IPv4 address. Choose port **5514** for a WsprryPi collector or the explicitly configured external collector port, including **514**. Hostnames, IPv6, loopback, broadcast, multicast and local interface addresses are refused. Station Wi-Fi is used; setup Wi-Fi does not carry the export.
3. Choose the maximum severity. Under **Export limits and event filter**, optionally select event codes and the rate/burst limits. An empty event list includes all approved export-safe event classes.
4. Choose **Save Pico UDP logging** and read back. Saved settings and the active revision are separate. After an uncertain reply or revision conflict, read settings again. Compare **Saved UDP logging settings** with the preserved draft and choose **Confirm review** before another save.
5. When the saved policy includes the test event, **Test saved UDP export** admits one finite diagnostic event. Check the destination independently. Local admission or submission counters cannot establish receipt.

A WsprryPi collector is configured under **Logs → Logging on this Pi → Receive network logs on this Pi**. Explicitly admit the Pico's observed station address as a peer. A Pi can also forward this Pico's already collected USB logs; that selection does not enable direct Pico UDP or USB collection implicitly. See the [Pi Logs guide](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Logs/index.html). External collectors receive an RFC 5424 message containing the compact project record. The Pi collector initially accepts this project profile rather than arbitrary syslog traffic.

For USB forwarding alone, leave this Pico's UDP export disabled. Enable its separate USB logging export, enable collection on the attached Pi, and select that saved Pico under the Pi's UDP forwarding controls. Admit the forwarding Pi's IPv4 address at the collector. The forwarded record retains the Pico's origin and adds one Pi relay observation. Enabling forwarding begins at the current journal tail; it does not replay old USB history.

## Interpret state and history

**Ready** means the sender is locally configured. **Awaiting network**, invalid destination, unavailable resources and local submission failure require separate attention. A successful UDP submission has receipt **unknown**. Queues are bounded and volatile; a link or profile change clears old-generation queued records, and records expire after five seconds. Filtering, queue loss and restarts create sequence gaps that cannot measure total network loss. Diagnostic text can be shortened to fit a datagram while identity and time fields remain intact.

Origin time, monotonic time and collector receipt remain distinct. Without origin UTC, the collector shows receipt time. Renaming a Pico changes its presentation but retains its device ID. Direct UDP, USB-forwarded UDP and physically checked USB are separate arrival scopes. UDP peer addresses and origin/relay IDs are claims, not authentication. Bounded duplicate suppression reduces repeated noise and is not an audit or reliable-delivery guarantee.

Compare the stable device ID, boot ID and sequence to relate copies received over different paths, then check the peer and relay observations. Restarting retains the device ID but starts a new boot identity and sequence. USB reconnection selects the saved physical device rather than whichever tty number appears first. Disconnecting USB leaves direct UDP available only if the Pico remains powered and connected to station Wi-Fi; removing its only power source stops both feeds. A stored source in Logs does not prove that the Pico is currently connected.

Logging checks require no radio transmission. Read back the settings, admit a finite test event when direct export is enabled and its filter permits it, and compare the collector's actual journal and Logs records. Check USB forwarding with finite startup or management-connection events. Keep local submission counts separate from observed receipt; UDP can lose an individual copy even when another arrival path succeeds.

## Preserve settings and stop export

Disable export, save, and read it back before removing or downgrading firmware. Ordinary restarts, unrelated setting saves and settings-preserving upgrades retain the independent UDP policy. Factory reset clears it. Corrupt or unsupported UDP saved state disables UDP rather than restoring an older enabled policy. USB logging remains independently configured.

Use the [shared USB installer](install.md) and retain its exact developer/release bundle. The UDP layout reserves two additional sectors below the existing NTP region; compatible images end below that reservation. Older images that extend into it are refused on rollback until a reviewed settings-preserving migration exists. An erase is not an automatic rollback procedure.
