# Phase 11.4 E2/E3 conflict acceptance results

E2 and E3 pass for the authorized single-Pico/controlled-host-claimant scope.
The [execution prompt](phase11-4-e2-e3-prompt.md) was executed on 2026-09-09.
The physical run passed on its first attempt. Adversarial review strengthened
the offline evidence checks; the repeated audit and eight negative checks passed.
No firmware, SDK, protocol, production application or UI repair was required.

This does not establish two physical boards' independent default names, CAs or
trust separation. E1 remains open. The controlled claimant deliberately advertises
the selected alias; it is not a second Pico performing a symmetric probe election.

## Bound identity and setup

| Item | Observed/tested value |
| --- | --- |
| Coordinating source | Clean devel `9f9cc8d8b4ac4db00595b0069a23388dadce2e45` before this slice |
| Board | Pico 2 W / RP2350, serial `0BF4B4AEC9FFB344`, attached to wspr5 |
| WTP device | `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| Firmware revision | `5ee5bcf93c56-dirty`, reviewed inhibited F2/F3/F6 implementation committed as `f187555` |
| Boot throughout | `cebcd4720cd9919a7cfaff492b717a85` |
| Engine | `inhibited-standalone-simulator` |
| Certified alias | `wsprrypico-0a60df.local` |
| Pico address/MAC | `192.168.1.47`, captured source MAC `88:a2:9e:0a:60:df` |
| Claimant | wspr5 `wlan1`, verified local IPv4 `192.168.1.117` |
| Server certificate SHA-256 | `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016` |
| Controller certificate SHA-256 | `c615a0f65d94c08bf65a776393f9d72c09f813fe59a1bfb2bd3ef4e6d023b0a1` |
| Job ID | `9916f371d0a347b99ac48f5863b80998` |
| Owner ID | `be2f7d8c3869457fb37d09b4cdd01943` |

The carried-forward deployed UF2 SHA-256 is
`2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4`;
ELF SHA-256 is
`f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65`.
Those image hashes belong to the previous deployment record; this slice verified
unchanged revision/boot/engine/deployment identity and did not reflash or reboot.

The single complete job used `rf-events/1`, tone mode, 15-second duration and
3,570,100 Hz, with ten-second ARM lead and a 500 ms start-uncertainty budget.
CAPS and synchronized GET_CLOCK admitted it. TLS 1.3 authenticated the original
DNS identity at the known Pico IP, selected `wtp/1`, and retained the same session
through the conflict. A separate authenticated HTTPS connection checked status
while the job was running and discovery was conflicted. One persistent USB
session provided independent authoritative observations.

The fixture used ordinary UDP from wspr5's own address, multicast group
`224.0.0.251:5353`, IP TTL 255 and only the exact certified alias's A record.
It sent 15 positive cache-flush records with TTL 120 at approximately one per
second, followed by two TTL-zero withdrawals. Its worker had a 22-second cap;
the controller stopped it after matching job completion. No foreign source IP,
router/lease change, system hostname, hosts entry, DNS configuration, service
installation, trust import, persistent Pico configuration or GPIO operation was
used. The installed WsprryPi service was not paused or modified.

## Physical observations

Private evidence is `build/phase11-4-e2-e3/`, with the physical run in
`e2-e3-conflict-20260909T160434Z`. The
[SHA-256 index](phase11-4-e2-e3-evidence.json) binds the runner, raw packet capture,
TLS/USB records, final peer reads and audit results. Generated/private artifacts
remain outside source control.

| UTC, 2026-09-09 | Observation |
| --- | --- |
| 16:04:36.299 | Baseline Pico A answer: original alias at `.47`, before conflict injection |
| 16:04:49.247 | Original job observed Running; host claimant then starts |
| 16:04:49.457 | Console reports conflict; TLS and USB both still report original job/owner Running |
| 16:05:04.196 | TLS and USB report that same job Complete with inactive output |
| 16:05:04.506 | Claimant stopped after two captured TTL-zero withdrawals |
| 16:05:06.550 | Conflict still latched after withdrawal; E2 observation complete |
| 16:05:06.575 | Owner RELEASE and independent empty/unowned confirmation precede explicit Wi-Fi retry |
| 16:05:12.445–12.771 | Three distinct captured Pico probe datagrams for the original alias and `.47` |
| 16:05:13.097 | Pico cache-flush A/PTR announcement at the original address |
| 16:05:18.725 | Active original alias, authenticated HTTPS/WTP and inactive/unowned cleanup verified |

**E2:** the actual observed outcome was that the Pico relinquished discovery
while the controlled host continued its claim. `mdns_state` became `conflict`,
the conflict counter increased from zero to one, and `advertised_hostname`
became empty. The configured certificate name remained unchanged. Neither the
Console history nor Pico A packets showed an alternate/suffixed name. No Pico
positive A answer appeared between the observed conflict and explicit recovery.

Independent TLS and USB observations retained the original device, boot, job and
owner while Running and at Complete. There was exactly one acknowledged LOAD
and one acknowledged ARM. Discovery conflict did not interrupt the inhibited
job, replace its owner or disable direct authenticated access. A failed resolver
lookup was not used as proof of conflict or completion.

**E3:** withdrawal alone did not clear the latch. After terminal evidence and
owner RELEASE, USB proved empty state, null owner/job and inactive output before
Console WIFI OFF/ON. The same boot reprobed and advertised the exact certified
alias; registration count increased from one to two while conflict count remained
one. The capture contains three distinct IPv4 probe datagrams followed by one
cache-flush announcement; these are receiver observations, not qualification of
on-air probe timing. No positive host claim appears during recovery.

Mac system resolution and Linux NSS subsequently returned only `.47`, with no
remaining `.117` answer. Both authenticated HTTPS reads passed against the original
server identity, same boot and inactive/unowned status. These are bounded recovery
observations, not sustained resolver reliability or measured cache-expiry timing.
The host fixture's TTL-zero withdrawal is not a Pico orderly-disable goodbye;
it does not close D2.

## Adversarial assessment and validation

The initial independent audit passed. Review identified incomplete audit checks
for several possible false positives and added explicit requirements for:

- Matching LOAD/ARM acknowledgements and unchanged job/owner/boot.
- A captured baseline Pico answer before the claimant and causal conflict order.
- Correct claimant source/destination, ports and hop limit; captured withdrawal.
- No Pico A advertisement during the conflict and no alternate name.
- A still-latched conflict after withdrawal, before explicit recovery.
- Fresh probe authority records before the recovered cache-flush announcement.
- No continuing positive claimant traffic during recovery, zero capture drops,
  and final authoritative cleanup with saved-state equality.

The strengthened audit was rerun on the retained original capture and passed;
the evidence did not need replacement. Eight deliberate negative checks reject
changed ownership, duplicate LOAD, automatic rename, missing recovery probes,
missing withdrawal, capture loss, cyclic DNS compression and truncated DNS.
The final adversarial assessment found no remaining actionable in-scope issue.

Executed checks:

```sh
cmake --build build/phase11-4-host --target mdns_tests mdns_lwip_tests --parallel 2
ctest --test-dir build/phase11-4-host -R '^mdns' --output-on-failure
python3 scripts/audit_phase11_4_mdns_conflict.py \
  build/phase11-4-e2-e3/e2-e3-conflict-20260909T160434Z
python3 build/phase11-4-e2-e3/adversarial.py
python3 scripts/validate_wtp_contract.py
```

Both responder suites passed, including the actual pinned lwIP parser/lifecycle
test. The offline packet audit passed with 26 captured packets and zero kernel
capture drops. Python compilation, documentation links, evidence hashes and diff
whitespace were checked. These tests do not claim RF timing, broad LAN behavior,
an overnight memory soak or remote CI execution.

## Cleanup and remaining scope

The fixture stopped, withdrew its alias and closed its temporary socket. The
Pico is empty, inactive and unowned, with the original matching completed job
retained in terminal history. Its unchanged boot has healthy storage, enabled
Wi-Fi, disabled power management, `pool.ntp.org`, station AA0NT/EM18/power 20,
disabled 120/0 schedule, expiry zero and watermark `1788714601000000000`.
Final service/provider checks show WsprryPi active and provider output disabled;
installed binary/configuration hashes match the preceding G4–G7 cleanup record.

Remaining Phase 11.4 work is B2 sustained Linux resolution reliability; D1 actual
DHCP reassignment; D2 captured Pico goodbye/cache expiry; D3 unexpected link loss;
E1 two real boards; and startup/overnight connectivity and memory investigation.
Phase 11.5 target resource/contention and 11.6 conducted RF remain separate.

## Documentation Impact

Added the prompt, results, hash index and offline-only packet audit tool; updated
the joint matrix and development/review entry points. Considered the mDNS,
WTP/browser and architecture contracts; none changed. No frontend or operator
workflow changed. The independent WsprryPi repository remains untouched.
The existing out-of-scope operator-documentation follow-up for network selection
and recovery remains; this acceptance-only slice adds no new operator procedure.
