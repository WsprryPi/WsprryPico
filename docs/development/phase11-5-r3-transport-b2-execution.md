# R3 B2: isolate the fatal-alert wait after the server handshake

Status: PASS for the B2 transport subset, independently audited and adversarially
reviewed. Executed under the user's request
to complete R3 and iterate through review findings. The unchanged 60 dB wiring
and retained test configuration remain in force. B1's two RF jobs and one Wi-Fi
cycle are consumed; this is a fresh, bounded packet, not a replay of B1 authority.

## Frozen packet

- Packet SHA-256: `b41cca02d4f6f34e773eed5e5d04b292104b184a2e30c318e5713d1c529a33a0`.
- Staging SHA-256: `92ebaec0ed07507d599f7e3e400eea71d87efbc05971eb447336898f2862edec`;
  808,960 bytes and 76 tooling/manifest files.
- Stager SHA-256: `167e0cee8c90f8246ec3071ab9f1fafcf2d949d0c56772489b904bddd9696cdf`.
- Fresh wspr5 root: `/home/pi/phase11-5-r3-transport-b2-20260913`.
- Nine private inputs are copied between existing paths **within wspr5 only**;
  none is in the uploaded archive. No credentials or generated firmware enter Git.
- Machine packet: `build/phase11-5-r3-transport-b2/stage/packet.json`.
- RF jobs: `7caa0cd278ce2ed860c8ca14b135e783` and
  `66c4c8c3068375966ccdfdc67459514c`, each exactly 100 seconds at 135,500 Hz.

Preserve the exact board, firmware, boot, 138 MHz/divider 1/RAM/GP2, production
binary and host/service identities in the [completion prompt](phase11-5-r3-final-completion-prompt.md).
A remains serial 0BF4B4AEC9FFB344, WTP fd6127d11d6aca42a9905fa3fb1bf1d5,
boot 9c5aec394269e0b57ca16d73ad3d12b6. Physical source is
2e43110f05304efdc2ae25c298baa0ef6426955b, UF2
7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6.
B remains CDDBF8767C506C07 / 29f20b7342051ef947aa56cb9d4fab42 /
feffcd075ab6cb0b74e7e0c2fde6c87f. Fresh read-only admission must prove these
identities, A inactive/unowned/healthy, B unchanged and retained configuration.

## Exact actions and limits

Stage and hash-check all inputs. Arm independent owned cleanup, then reuse the
isolated wlan0 AP/wlan2 client fixture. Protect eth0/wlan1 management, installed
WsprryPi, chrony/GPSD/Avahi/permanent time.local, B, GPSDO, SDR and Pi GPIO4.
Fixture lifetime is at most 1,800 seconds plus 600 seconds cleanup; at least
375 seconds must remain before the RF observation. No CONFIG saves, flash,
reboot or heap probes. Keep the test configuration and unchanged conducted path.

Permit at most **one new idle Wi-Fi OFF/ON cycle** after fresh same-boot,
inactive/unowned admission with enabled Wi-Fi, no address and NONET/BADAUTH.
Connected skips recovery. The existing 30-second JOINING/NOIP read-only wait,
write-ahead commands, no retry of uncertain ACKs, early DHCP/ARP/mDNS/NTP capture
and AP journal/station checks remain unchanged. Network readiness requires
10.77.15.10 and synchronized clock before RF. Any failed prerequisite stops RF.

Run at most the two frozen Tones, 200 seconds total, on the previously confirmed
60 dB, 50-ohm wiring. This consumes at most two of the remaining 33 jobs and
200 of 3,723.68 RF seconds. The sole USB observer owns both jobs, arms ten seconds
ahead with at most 500 ms uncertainty, and allows twelve total 60-second lease
renewals. The second job requires first-job pressure success and released idle
state. The separate pinned production controller is RF-off for 300 seconds;
INFO/STATUS/host observation lasts 360 seconds. Preserve all prior cadence,
five-second read deadlines, 32 KiB heap reserve, two 4 KiB guards, zero unexpected
allocator failures and full/short DMA/launch/tail timing requirements.

Execute all fourteen [B1 cases](phase11-5-r3-transport-b1-execution.md) with
fifteen pressure TCP connections and eight verified HTTPS controls, without
retries. Partial headers and bodies retain separate 15-second activation
checks; pending expiry retains the established holder and separate ten-second
timer; the stalled reader stays unread and open through successful fresh slot
reuse. TCP capture, clock mapping and zero kernel drops remain required.

The failed-alert wait uses the prospective schema `phase11.5-r3-transport-b2-v1`
and policy `zero-payload-after-server-flight-v1`. B1 retains its original schema
and failed outcome. B2 first receives and verifies the **complete server TLS
handshake flight** with normal acknowledgements. OpenSSL completes its client
handshake locally, but the MemoryBIO's final client bytes remain withheld.
Record that boundary, install the filter, then send those final client bytes.
This lets the final data-bearing ACK acknowledge the complete server flight
before the target emits its missing-certificate fatal alert.

Create one unique `r3b2_<nonce>` nft table only inside the owned client namespace.
Every drop rule matches source 10.77.15.2, destination 10.77.15.10, this socket's
ephemeral port and destination 18443. Eleven mutually exclusive header-length
rules pair IPv4 IHL=5 with TCP data offsets 5–15 and IP total length 40–80.
That equality proves **zero TCP payload**. Drop ACKs only; SYN/FIN/RST and every
data-bearing packet pass, including data lacking PSH. No global, management or
persistent firewall change. Log write-ahead scope, exact rules, counters and
removal; delete in finally even if counter capture fails. Independent namespace
cleanup is the backstop. Require the filter still present until target closure.

Reassemble both TCP directions, preserving retransmissions and sequence wrap,
and match all client-recorded ciphertext. Require target alert 116, unacknowledged
alert bytes, nonzero empty-ACK drops and target close approximately one second
after the alert's first transmission. Compare with the acknowledged control,
which must actually ACK the alert and close under one second. Both need fresh
verified recovery within fifteen seconds. Client closure cannot establish the
failed-alert path. A capture missing the intended trigger fails acceptance.

## Pre-execution evidence and review

B1's [independent failure reconstruction](phase11-5-r3-b1-failure-result.json)
proves ClientHello delivery, repeated unacknowledged ServerHello, no fatal alert,
and premature filter activation. It also proves two complete Tones, 360 INFO /
72 STATUS / 72 health samples over 360.015835891 seconds, normal timing, final A
inactive/unowned, B unchanged, filter removed and host restored. Twelve case
finishes are diagnostic only. B1 gains no acceptance credit.

The corrected rules passed check-only validation on wspr5 and an actual Linux
loopback test in a newly unshared namespace containing only `lo`: 66 packets,
55 passed, exactly eleven empty ACKs dropped. All eleven TCP header lengths,
data with/without PSH, SYN, FIN and RST were exercised. Proof SHA-256:
75cdf3ce93de7842608d80bd40932ef9b9fe9e4543249fb82f1992749699eb53.
The first loopback test exposed that raw-IP OUTPUT drops return EPERM; the test
now records that expected result and still requires independent packet/counter
agreement. No Pico, RF, existing interface or host firewall participated.

A real OpenSSL MemoryBIO client/server test independently verifies that the
client final flight remains withheld until filter readiness and that sending it
then produces the expected missing-certificate fatal alert. Old B1 policy cannot
acquire B2 scoring. Eight mutations of the real B1 archive are rejected. All
224 Phase 11.5 tests completed: 222 passed, two unrelated private tests skipped;
nine available R3 archives were supplied. No firmware or Pi runtime change.

Any failure stops later injections/jobs and preserves the packet. Keep observation
through its original bound where possible, reconstruct raw output, and classify
the cause before declaring a firmware failure. Reconcile only known complete,
inactive jobs, verify A/B/host restoration and retain the test configuration.
Independently audit and adversarially assess the new evidence. Continue all
remaining capacity, USB, retention and reclamation tests; B2 alone cannot close R3.

## Recorded execution result

All fourteen cases passed, with two complete 100-second Tones (epochs 9 and 10),
300 seconds of production traffic and the complete 360-second observer window.
One declared idle Wi-Fi cycle was consumed. No CONFIG saves, flashing or reboot
occurred. Final A was Empty/inactive/unowned; B was unchanged and the host fixture
was restored. The evidence archive SHA-256 is
`b2359326fe3faa870ec800e2f5f2a5a24fd709c25a5e073a4cff6c435de39c44`
(10,854,400 bytes, 168 files). RF subpacket SHA-256:
`41ec772a76a91286c9a3caf29b486bf1b56dcbe61ed433b064847d0c7a004f14`.

The independent [machine result](phase11-5-r3-b2-result.json) agrees with the
recorded audit. Adversarial review found the auditor did not independently check
every installed nft rule field; it now checks actual table/chain, tuple, header
lengths, flags, counters and byte counts. The unchanged original capture passes
the stricter audit. Sixteen deliberate raw-evidence mutations are rejected, and
a second intact audit produces the identical result. No physical rerun was
needed for that evidence-checking repair. R3 remains OPEN.
