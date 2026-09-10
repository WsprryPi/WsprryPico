# B2/D2 three-radio acceptance

**B2 and D2 pass the controlled native Linux acceptance scope.** Eight consecutive
full OFF/ON cases passed on 2026-09-10, using all three wspr5 Wi-Fi radios and
Ethernet management. The Pico retained one boot through the entire
29.3-minute corrected series. Both independent Linux
clients completed native resolution and authenticated WTP/HTTPS checks in every
case: **96 authenticated checks**, including baselines and five recovery checks
per client per case.

The [execution prompt](phase11-4-three-radio-prompt.md) fixes the procedure and
acceptance limits. The [sanitized evidence manifest](phase11-4-three-radio-evidence.json)
binds the firmware, hardware, observations, restoration and private evidence index.
Earlier diagnostic evidence remains private. This record describes the working
arrangement; it does not attribute historical infrastructure failures to a cause.

## Working arrangement

| Role | Hardware | Test configuration |
| --- | --- | --- |
| Management | Ethernet `2c:cf:67:62:76:64` | Original wspr5 connection; Mac remains on its normal network |
| Access point | Onboard wlan0 `2c:cf:67:62:76:66` | Channel 11, WPA2/CCMP, `10.77.14.1`, private DHCP/NTP |
| Native client 1 | USB wlan2 `e8:4e:06:ae:d7:09` | `10.77.14.2`, independent network/mount namespaces and Avahi/NSS |
| Native client 2 | USB wlan1 `90:de:80:47:b9:da` | `10.77.14.3`, separate network/mount namespaces and Avahi/NSS |
| Device | Pico A `fd6127d11d6aca42a9905fa3fb1bf1d5` | `10.77.14.10`, certified `wsprrypico-0a60df.local`, TLS 18443 |

The private AP has no forwarding, NAT or default route. No Netgear configuration,
system package, global trust, firmware flash or RF/job action was needed.
WsprryPi remained active. The original Wi-Fi recovery timer was suspended only
while wlan1 served as the second client. A 50-minute independent restoration
timer was armed before the first network mutation and stopped after verified
restoration.

## What works

The observer resumes **one distinct logical WTP session per client**, reconnecting
with fresh request IDs. This matches WTP's session-resumption contract and keeps
repeated status checks within the server's bounded session capacity. The server
retains up to 16 logical sessions; unowned sessions expire after five minutes
without activity. Creating a new session per poll is unsuitable for a repeated
observer. The helper now accepts a validated
optional session identity. The corrected campaign used two client sessions and
288 unique WTP request IDs, with no session churn or replay across cases.

Each case retained a full 150-second OFF interval. All three NICs captured the
matching TTL-zero A and PTR goodbye, three same-name probes, and recovery
announcements. Each native client returned negative results at six distributed
points through and beyond the old 120-second TTL. The first negative lookup
completed within **8.07 seconds** of OFF;
this is an observed upper bound, including the resolver's lookup time, rather
than a precise cache-removal callback timestamp.

After ON, local advertisement returned within **4.42 seconds**.
Both clients' first authenticated checks completed within
**9.13 seconds**. Every client completed
at least five recovery checks spanning more than 30 seconds within the original
120-second deadline. TLS clock admission was respected without extending that
bound. Each case's raw USB framing, contiguous Pico trace, packet counts and
zero kernel capture drops passed audit. Independent USB coverage gaps stayed
below **1.68 seconds**, within the fixed two-second limit.

| Case | Local active (s) | Client 1 authenticated (s) | Client 2 authenticated (s) | B2 / D2 |
| --- | ---: | ---: | ---: | --- |
| 1 | 4.41 | 6.17 | 7.86 | PASS / PASS |
| 2 | 4.40 | 6.85 | 8.56 | PASS / PASS |
| 3 | 4.40 | 6.21 | 8.47 | PASS / PASS |
| 4 | 4.40 | 6.84 | 9.13 | PASS / PASS |
| 5 | 4.40 | 6.18 | 7.98 | PASS / PASS |
| 6 | 4.41 | 6.14 | 7.84 | PASS / PASS |
| 7 | 4.40 | 6.14 | 8.42 | PASS / PASS |
| 8 | 4.40 | 6.71 | 8.43 | PASS / PASS |

Campaign boot: `fff66c8831bc91a6bed56a57e27f68db`. Runtime: `802c91a7b86e-dirty`, standard
`inhibited-standalone-simulator`, SDK 2.3.1, 150 MHz. The previously verified UF2
SHA-256 remains
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`;
[source and flash provenance](phase11-4-radio-results.md) is unchanged. All USB
and authenticated status observations agree on inactive/empty/unowned output,
healthy storage, unchanged saved state and zero network allocation errors.

## Review and reusable checks

Review closed the observer session-churn defect, made optimized execution an
explicit refusal, and strengthened offline checks for WTP schema/request/session
identity, native lookup pairing, separate client caches and complete packet
lifecycles. Hardware-free validation passed **55 checks**. Adversarial assessment
rejected **216 per-case mutations** and **six campaign mutations**, including a
missing goodbye with otherwise valid capture structure/counts, a seven-case
campaign, session churn between cases, reused request IDs and a missing device control
acknowledgement. Reassessment of
all original evidence passed with no remaining actionable finding in this slice.

```sh
python3 -B tests/phase11_4_three_radio_tests.py
python3 -B scripts/phase11_4_three_radio_campaign_audit.py <private-series-directory>
python3 -B scripts/phase11_4_three_radio_adversarial.py <private-case-directory> --resumed-sessions
python3 -B tests/phase11_4_three_radio_campaign_adversarial.py <private-series-directory>
```

The audits operate only on evidence files. The hardware fixture is an opt-in
wspr5 engineering tool, requires `--run`, and is not an end-user provisioning
installer. A fresh private root contains the existing credential references,
original Wi-Fi configuration, helper sources and WTP schema. The fixture's
`setup`, `campaign --series series-N` and `cleanup` commands follow the prompt;
the independent restoration timer bounds the entire deployment.

## Verified restoration and remaining scope

Pico A returned to Bohica-IoT at `192.168.1.47`, with cleanup boot
`9bcab75c38e37699fac74075cb64ffc9`. Pico B remained unchanged at `192.168.1.53`,
boot `4e2fb851c08b278dd4b977104d2c2aaa`. Fresh INFO and WTP checks confirmed
both devices inactive, empty and unowned, with their original firmware and saved
settings. Only A's temporary AP configuration required setup/cleanup reboots;
no reboot occurred inside the eight-case campaign.

All original host routes and radio power settings were restored. wlan1 returned
to its original Bohica-IoT profile and BSSID `7a:cd:d6:f2:f6:c5`, with power save
off; wlan0/wlan2 returned down with their original power settings. Ethernet and
WsprryPi stayed available. Wi-Fi recovery is active and boot-enabled. Ordinary
Wi-Fi SSH passed three independent checks in 0.58–2.89 seconds,
with the return route verified through wlan1. No campaign process, namespace,
temporary AP profile or test NTP allowance remains active. Existing user shutdown
and soak work is byte-for-byte unchanged.

**B2 and D2 are closed for this bounded controlled Linux scope. The eight-hour
uninterrupted memory/connectivity soak remains open**, so Phase 11.4 is not yet
complete. These results do not qualify other infrastructure or macOS compatibility,
explain every historical failure, or establish permanent reliability.
