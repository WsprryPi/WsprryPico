# Phase 11.5 Package 10 execution and adversarial review

## Outcome

Package 10 is **blocked before corrected RF admission**. R6 remains **OPEN** and
Phase 11.5 remains **5 of 6 families closed**, with no accepted complete
configuration. The corrected matched replay-state workload did not run, so this
package neither passes nor fails the Package 9 resource-return measurement.

The [execution prompt](phase11-5-package10-prompt.md) freezes the intended
workload and unchanged 1,024-byte gate. The
[sanitized failure result](phase11-5-package10-failure-result.json) binds the
private preflight history, actual RF accounting, final inventories and restored
host state. The
[failure adversarial result](phase11-5-package10-failure-adversarial-result.json)
records the publication assessment. Credentials, captures and authenticated
payloads remain private on `wspr5` under the retained evidence roots.

## Package 9 diagnosis and corrected design

Package 9's 12 KB post-N offset is consistent with a required retained
383-entry production adjustment vector. WTP/1 keeps terminal records and exact
LOAD results replayable for at least one hour. Package 9 established its
baseline with a different 512-entry class and compared terminal histories with
different ages and class contents. Package 10 therefore selected measurement
normalization, with no firmware or protocol change and no relaxed threshold.

The corrected packet freezes three one-second 383-event production-class jobs,
five one-second 512-event maximum-class jobs, the original three 600-second
normal cycles, five final maximum-class refresh jobs and an equivalent final
terminal set. Its production frequencies match WsprryPi's actual 135.505 MHz
mark and 135.500 MHz space sequence. The planned corrected packet is 16 jobs /
356.8 RF seconds. It did not reach reservation or RF.

Package 9 remains a failed measurement. The diagnosis above is supported by
source and retained evidence, but the corrected physical comparison required to
accept it did not occur.

## Execution chronology

The first Package 10 packet completed four one-second warm-up jobs. An
independent retained-TLS comparison then showed that its production-class
normalizer used the wrong frequency pair. The packet stopped before a baseline,
normal cycle or acceptance measurement. That attempt remains charged as four
jobs / four RF seconds in
[its immutable result](phase11-5-package10-attempt1-result.json).

The corrected execution then exposed fixture readiness failures before RF. The
13 private corrected preflight roots are retained because each froze a new
helper or readiness repair. They are tooling iterations, not thirteen product
failure scenarios and not thirteen RF attempts. Five reached the campaign
runner but stopped in network/clock, name-resolution or TLS readiness. Eight
stopped while creating the independent wireless client. None acquired the RF
reservation, completed a normalizer or transmitted.

The final bounded repair combined all evidence-supported changes that had not
previously been tested together:

- restored the historically qualified wlan0 AP / wlan2 independent-client
  roles;
- reset the identity-checked Broadcom SDIO and MT7921 USB drivers before setup;
- bound association to the exact AP BSSID and channel;
- allowed 90 seconds for association and 105 seconds for client readiness;
- separated route proof, a quiet 180-second clock settle and bounded WTP
  readiness;
- reduced the TLS 1.3 ClientHello to one packet by selecting X25519 for both
  Python clients and the WsprryPi process; and
- retained independent timed cleanup before the first host mutation.

The final packet was
`11c29234218383408394fcca61d3d9d21f5dc2e7f8c270e00d7c04a72606c75c`.
Its independent wlan2 client repeatedly attempted authentication with the exact
wlan0 BSSID, then reported connection failure and never created the readiness
marker. The fixture stopped and restored automatically. A preceding packet also
tested the reverse radio roles and failed association. Replacing the independent
client with a host-local connection would weaken the frozen evidence model, so
that shortcut was rejected.

## Actual finite budget

The Package 10 authorization was 480 additional RF seconds. Actual cumulative
use is four jobs / four RF seconds, all from the stopped first packet. Corrected
preflights used zero RF. No flashes, BOOTSEL transitions, configuration writes,
controlled reboots, intentional DUT Wi-Fi cycles or allocation probes occurred.
The 476 unused seconds remain unused; the frozen prompt forbids treating that
remainder as an automatic retry allowance.

## Raw and adversarial review

The raw-failure auditor reconstructs all thirteen corrected preflights from
their packets, fixture journals, client logs and campaign journals. It rejects
any root that acquired the reservation, started capture for RF, completed a
normalizer or began a production cycle. It also independently checks the final
packet, both radio-role assignments, cleanup records, released reservation and
fresh A/B USB inventories.

Review of the auditor and shared fixture found three issues:

1. older preflight helpers used literal wlan0/wlan2 assignments rather than the
   later constants, so the auditor initially could not identify their roles;
2. early 20-second association windows ended before wpa_supplicant emitted a
   `CONN_FAILED` event, although they retained authentication attempts, no
   connected event and the worker assertion;
3. the Package 10 association window, BSSID binding and pre-setup radio resets
   initially flowed through the shared fixture for historical Package 7-9
   schemas. They were limited to the Package 10 schemas, preserving the frozen
   behavior of earlier packets.

The first two rules were repaired to validate the actual retained evidence
without weakening the failure condition, and the intact raw audit passed. The
shared-fixture controls were then scoped to Package 10 and the affected tests
were rerun.

The adversarial assessment independently changed 24 closure-critical facts. It
rejected false R6 closure, acceptance credit, a fabricated corrected RF run,
changed actual/unused budget, relaxed resource or fixture requirements, altered
radio roles and history, output-active final state, unreleased reservation,
incomplete host restoration and corrupted evidence hashes. The intact result
passed again after every mutation was rejected.

## Validation and final state

The Package 10 and network-fixture suites pass 45 focused hardware-free tests.
The complete host build and all 80 registered tests pass after refreshing only
the generated one-day host-test certificate in `build-host`. Python syntax,
JSON parsing and repository whitespace checks pass.

Fresh final USB inventories show:

- Pico A source `91933c009709`, boot
  `ff719d304f1ba4ac23fddd93561b26f0`: Empty, unowned, output inactive;
- Pico B source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`: Empty, unowned, output inactive.

The shared RF reservation is Released. The host fixture removed its namespace,
test subnet and AP profile, returned wlan0/wlan2 down, restored the installed
WsprryPi service and left the Wi-Fi recovery timer active. Management Ethernet
and wlan1 remained available.

## Remaining work

Qualify the independent wireless client path in a separate zero-RF fixture
packet before another R6 campaign. The best bounded next step is to replace or
move the independent station to a separately controlled adapter/host, then
require stable association, mDNS, NTP and authenticated WTP/HTTPS traffic for a
fixed readiness interval. Do not spend RF on that diagnosis.

After the fixture passes independently, freeze one new complete corrected
Package 10 packet. Preserve the 1,024-byte gate, Package 9 failure and matched
3/5 replay-class design. R6 and Phase 11.5 remain open until that full physical
packet and its raw/adversarial audits pass.
