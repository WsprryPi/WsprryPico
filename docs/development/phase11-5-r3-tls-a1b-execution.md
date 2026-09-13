# R3 A1b execution packet — prepared, awaiting approval

**Consumed historical packet:** A1b failed at the first HTTP check; one Tone
completed and the second was not submitted. The [failure review](phase11-5-r3-tls-a1b-failure-review.md)
records the repairs and the user's subsequent choice to retain the test
configuration. Do not replay the preparation below.

This fresh packet uses the corrected INFO/STATUS binding after the
[consumed A1 failure and restoration](phase11-5-r3-tls-failure-review.md).
Its [review](phase11-5-r3-tls-a1b-review.md) and
[machine-readable record](phase11-5-r3-tls-a1b-prepared.json) identify the exact
staged bytes. No A1b staging or hardware operation has occurred. Phase 11.5
remains OPEN, 2/6 families closed, with zero accepted R3 physical assertions.

The supervisor must re-audit the preserved failed attempt before host setup.
It admits only that packet's restored A/B identities and cumulative CONFIG 36.
The separate scope `R3-A1b-config-36-to-38-v1` permits one setup CONFIG and one
original CONFIG restoration. The consumed 34→36 allowance remains exhausted.

## Frozen identity and transfer

- DUT A: USB `0BF4B4AEC9FFB344`, WTP `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Comparator B: USB `CDDBF8767C506C07`, WTP `29f20b7342051ef947aa56cb9d4fab42`; read-only.
- Expected initial inhibited A boot `7a772a4eb283b23afdd1e25acbc449cd`,
  firmware `802c91a7b86e-dirty`; B boot `feffcd075ab6cb0b74e7e0c2fde6c87f`,
  firmware `dbf1d86f0885-dirty`. Fresh admission must establish both again.
- Host `wspr5`, boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Use SSH outside the sandbox.
- New private root `/home/pi/phase11-5-r3-tls-a1b-20260912`, mode 0700.
  Existing roots or partially staged attempts cannot be overwritten or replayed.
- Local archive `build/phase11-5-r3-tls-a1b/staging.tar`: 4,710,400 bytes, 61 files.
  SHA-256 `a9df73f3eb61f7893ce899defc6d3df88a2dcee198da0a636a7e8822fd73de3c`.
- Packet SHA-256 `590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218`.
- Staging helper `scripts/phase11_5_r3_tls_stage.py`, SHA-256
  `788fb4c6595506916763229e900b6c9ccb0f7f941b0192eb282e1b2ad4e6830f`.

Transfer the archive and that helper to new files
`/home/pi/phase11-5-r3-tls-a1b-20260912.tar` and
`/home/pi/phase11-5-r3-tls-a1b-20260912-stage.py`, without overwriting existing files.
The helper verifies all archive members before creating the private root. It then
copies exactly nine hash-bound existing files from
`/home/pi/phase11-5-r3-tls-a1-20260912`: original UF2/configuration, the native
TLS observer library, and CA/certificate/key triples for browser and controller.
Private keys stay on wspr5. All source paths and hashes are in the frozen packet.
Staging alone performs no hardware or service operation.

After explicit approval, stage once on wspr5:

```sh
sudo python3 /home/pi/phase11-5-r3-tls-a1b-20260912-stage.py \
  --archive /home/pi/phase11-5-r3-tls-a1b-20260912.tar \
  --root /home/pi/phase11-5-r3-tls-a1b-20260912 \
  --archive-sha256 a9df73f3eb61f7893ce899defc6d3df88a2dcee198da0a636a7e8822fd73de3c \
  --packet-sha256 590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218 --run
```

Then execute once on wspr5, preserving stdout/stderr in the new evidence root:

```sh
sudo python3 /home/pi/phase11-5-r3-tls-a1b-20260912/scripts/phase11_5_r3_tls.py \
  --root /home/pi/phase11-5-r3-tls-a1b-20260912 \
  --packet-sha256 590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218 --run
```

Packet scope fields do not authorize execution. The existing wiring confirmation
is retained, but this fresh staging/fixture/RF packet and its two additional
CONFIG writes require explicit approval before these commands run.

## Images, RF path and finite jobs

Pinned firmware source `2e43110f05304efdc2ae25c298baa0ef6426955b`, embedded
`2e43110f0530`; physical 138 MHz, divider 1, RAM rendering, listener on, GP2
PIO/DMA engine. No rebuild or firmware implementation change accompanies A1b.

| Image | SHA-256 |
| --- | --- |
| Physical UF2 | `7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6` |
| Inhibited UF2 | `c9069bdd3dea14fef205ae38f8780d7e798442420b6738baa44f8c1e585a2938` |
| Original inhibited UF2 for restoration | `25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10` |

The user's explicit unchanged-wiring confirmation from A1 carries forward.
The confirmed conducted path is:
A GP2 → 20 dB → combiner; B GP2 → its 20 dB → combiner; LB-1420 GPSDO → its
20 dB → combiner; combiner → 20 + 10 + 10 dB → SDR. Each path has 60 dB total
attenuation and 50-ohm loads, with no RF filters. No B output, GPSDO setting,
wspr5 GPIO4 operation, SDR configuration change or radiated test is included.
If this path has changed, stop before new RF and revise the packet.

| Job | Submission | Frequency / duration | ID |
| --- | --- | --- | --- |
| A1b-1 | Sole USB observer/actor | Tone, 135,500 Hz, 100 seconds | `91bd2c3d57e3e74f7de183203796f463` |
| A1b-2 | Same USB actor | Tone, 135,500 Hz, 100 seconds | `b9a5db8b8e5b81e0a2a86ee7508e8f88` |

Total RF-on allowance: **200 seconds**. Each job contains one RF-on event.
Each has its own CLAIM/LOAD/GET_CLOCK/ARM/completion/RELEASE; ARM is ten seconds
ahead on the synchronized target clock, with 500 ms maximum admitted uncertainty.
The owner is frozen in the packet; twelve 60-second lease renewals are the
combined maximum. No retry, automatic abort or replacement job is authorized.
The second job requires successful first-job pressure results and released idle
USB authority. CAPS admission is repeated on the selected physical boot.

The 110.592-second global duration restriction is left unchanged. These two
jobs fit that candidate; they do not resolve or qualify longer QRSS support.

## Pressure and observation

The existing production binary remains RF-off and holds one authenticated WTP
connection for 300 seconds. Source is
`6f65d5c7d202569102459ab68d7c9ea079b96f35`; executable SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
This is a separate test executable, not installed WsprryPi. The administrative
cadence uses the accepted `single-flight-admin-v1` policy: one Hz when free,
five-second native transaction deadline, retained in-flight delay, no exemption
for host scheduling lateness. The normal browser workload is disabled; six
explicit fresh HTTPS controls/recoveries belong to this pressure profile.

| During Running RF | Exact trigger / result |
| --- | --- |
| A1b-1 positive | Fresh TLS 1.3, verified target certificate, HTTP/1.1 GET `/api/v1/status`, correct owner/job/boot; two active connections, zero pending |
| Missing client certificate | One client without a certificate; target fatal alert 116 within five seconds; arbitrary EOF and client-side certificate validation are failures |
| Certificate recovery | Fresh authenticated HTTPS; target admission delta two, no timeout or TCP-admission rejection |
| Silent handshake | One TCP client sends no TLS bytes; close within 12 seconds after client connect; target timeout delta one, followed by fresh HTTPS |
| A1b-2 positive | Fresh authenticated HTTPS while the same production WTP connection continues |
| Slots / excess | Hold a silent active handshake and a pending TCP socket; open one excess connection and observe EOF/reset within two seconds. Both held sockets must remain open until the client closes them. Fresh HTTPS proves rejection delta one and bounded admissions |
| Duplicate WTP | One fresh, authenticated TLS 1.3 `wtp/1` connection using the controller certificate; target closes within two seconds after handshake. No WTP application bytes or new logical session are sent |
| WTP recovery | Fresh authenticated HTTPS; original production connection/session must remain intact |

There are twelve pressure TCP connections total, without retries. Recoveries must
finish within fifteen seconds of the preceding trigger's completion, including
cleanup delay. Positive HTTPS has a fifteen-second total bound. Handshakes and
pending sockets are distinct: A1b does **not** claim pending expiry, failed-alert
one-second wait coverage, HTTP 15-second timeout coverage, or the general
30-second progress timeout. Client-observed silent close plus a target timeout
counter does not supply a target accept/activation timestamp.

The separate USB observer runs 360 seconds: INFO one Hz, STATUS and host health
at five-second intervals, with existing sampling/deadline checks. Every pressure
case requires fresh INFO and STATUS evidence of owned Running RF. Console INFO
supplies the scheduler RF state and top-level launch epoch; WTP STATUS supplies
job/owner authority. Both must agree on boot and Running/active state. The epoch
must advance for each job and remain fixed through its pressure cases. See the
[actual response field map](phase11-5-metrics.md). The offline
audit independently brackets each case with raw-audited USB samples, reconstructs
HTTPS framing/body and target counters, and verifies actual production TLS wire,
finite lifecycle, exact per-job DMA/refill/launch/tail deltas and complete release.

Retain the 32 KiB heap reserve, unchanged allocator/TLS failure counters, both
4 KiB stack guards, and the R1 demonstrated largest request bound of 18,364 bytes.
Full-block critical budget remains 2,849,391 ns; short predecessors require their
own word counts and at least 25% reserve. No overlapping maxima are added, and
cumulative worst values remain cumulative. No allocation probes occur.

## Fixture, budgets and restoration

Activate only the owned isolated three-radio fixture: wlan0 MAC
`2c:cf:67:62:76:66` is AP, wlan2 `e8:4e:06:ae:d7:09` is the independent client;
eth0 `2c:cf:67:62:76:64` and wlan1 `90:de:80:47:b9:da` retain management.
Use isolated network/mount namespaces, AP `10.77.15.1`, client `.2`, DUT `.10`,
and no NAT, forwarding or management-LAN default route. Temporary owned DHCP,
Avahi/time.local publication, chrony allowance and diagnostic captures are
included. Pause and restore the existing Wi-Fi recovery timer through its owned
fixture lifecycle. Preserve permanent time.local, chrony/GPS-PPS/Avahi and the
installed WsprryPi process/executable. No link-loss, DHCP-change or Wi-Fi cycling
fault injection is included.

Carry **CONFIG 36 forward to a maximum of 38**, with probes unchanged at six.
A setup CONFIG write installs the isolated network with schedules still disabled;
the other write is reserved for restoring the original configuration, SHA-256
`2978a00337f174286085251ec12ea15d0e524652738e009af3eb64e3be4ca0bf`.
Normal CONFIG persistence may rotate its journal internally. No extra deliberate
journal-rotation writes/erasures, R5 schedule installation or heap probe is granted.

Arm independently owned device restoration before the first board mutation.
Take serial-specific A/B admission evidence and back up A before flashing the
pinned inhibited candidate, applying setup CONFIG and its explicit reboot, then
switching to the pinned physical candidate. These are three planned flashes
including the final original-image restoration, and one explicit CONFIG reboot.
Required BOOTSEL transitions and read-only backups belong to those flashes.

Device runtime is bounded to 1,800 seconds plus a 600-second guarded restoration
window. The host fixture is bounded to 3,600 seconds plus 600 seconds cleanup;
setup has a 300-second bound and radio return has sixty seconds within cleanup.
The host must outlive the device window plus its cleanup reserve. Ordinary work
should finish earlier; these are ceilings, not a request for more RF time.

On success, release both finite jobs, establish authoritative inactive/unowned
state, restore original CONFIG and inhibited image, verify A configuration and B
identity/configuration unchanged, then restore the host fixture and permanent
services. Counts must finish at CONFIG 38 and probes six.

An unknown write, unexpected boot, fault, failed worker or lost observation stops
dependent actions. Keep raw evidence and attempted counters. The USB observer
continues to its original deadline where possible. No automatic ABORT, reboot,
reflash, retry or fault clearing is authorized to turn failure into a pass.
Restoration requires authoritative admissible state; unknown output remains
unknown. Host cleanup is independently allowed and cannot reset an unknown Pico.

## Approval boundary

The user's attached handoff, section 10, requires: “Carry the existing count
forward and obtain a concrete new allowance.” It also requires a new bounded
fixture/RF packet because all earlier windows are spent. The repository's
[hardware rules](../../AGENTS.md) require explicit authorization for flashing,
USB control and RF output. This packet is the concrete approval request for
staging, the listed fixture/device operations and CONFIG 36→38, using the already
confirmed unchanged conducted wiring. Local implementation, tests and publication were already
authorized and do not need another grant.
