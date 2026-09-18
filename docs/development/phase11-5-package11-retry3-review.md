# Phase 11.5 Package 11 Retry 3 review

## Decision

**STOPPED — no R6 credit.** Retry 3 cleared the retained-terminal and memory
gates, completed all eight replay-history warmups, passed the 360-second
matched baseline and completed the first 600-second native/browser interval.
The runner then rejected the cycle at `USB lifecycle/cadence`. The campaign did
not produce the three post-N windows, refresh set or final-Q window required for
R6 acceptance.

The failure is a host harness evidence-reduction defect. It is not a Pico
lifecycle, USB cadence, RF, capture or resource failure. A fresh physical
campaign remains required after separate authorization.

## Executed packet and finite accounting

- Authorization: `PACKAGE11-TWO-HOST-R6-RETRY3`.
- Packet SHA-256:
  `f2f0e684b658310038dd6b3a36b8b58ef285c1db6bd6fcbf05a9c4111b153dbd`.
- The terminal-retention gate passed on its first packet-bound inventory with
  zero retained records.
- The unchanged memory gate passed on its first sample at 193,736 available
  bytes against the 165,000-byte threshold, with zero allocator failures.
- Eight one-second warmups and one 114.6-second production job accepted ARM.
  Retry 3 therefore charges 9 jobs / 122.6 planned RF seconds.
- Cumulative Package 11 accounting is 25 jobs / 138.6 planned RF seconds.
- No flash, BOOTSEL transition, CONFIG write, controlled reboot, intentional
  Pico Wi-Fi cycle or allocation probe occurred.
- Unused Retry 3 allowance does not authorize another campaign.

## What failed

Cycle 1 ran the full 600 seconds. WsprryPi's native report recorded a complete
handoff and complete output-inactive job. The independent USB observer produced
120 STATUS samples with 4.999961309–5.000065331-second spacing, a maximum
954.628630-millisecond response, and no observer or worker failure. Its final
STATUS was Empty, unowned and output-inactive with the matching complete,
output-inactive terminal record in the eight-record set.

The same USB session received six events, including the five `JOB_STATE`
transitions Loaded, Armed, Running, Complete and Empty. The old observer left
those events pending while selecting each STATUS response and reduced only the
five-second STATUS snapshots. Those snapshots saw Empty, Armed and Running;
the Complete state was shorter than the polling interval. The status-only
predicate therefore rejected valid USB evidence after Cycle 1.

## Repair and host-only retest

The observer now journals pending USB events, rejects adverse events, and keeps
event and STATUS evidence separate:

- USB events prove transient Loaded, Armed, Running and Complete transitions.
- Periodic STATUS proves boot identity, cadence, live Armed/Running coverage,
  final Empty/unowned/output-inactive authority and the retained complete
  output-inactive terminal record.
- The raw auditors apply the same split and bind events to the expected WTP
  session and protocol, and lifecycle events and terminal records to the cycle
  job.

The repaired reducer was replayed against the exact private Retry 3 journal and
raw USB stream. It passed with zero Pico, USB, network, service, reservation or
RF access. The published aggregate
[retest result](phase11-5-package11-retry3-usb-reducer-retest-result.json) is
bound to both private evidence hashes and the repaired source. Its
[adversarial assessment](phase11-5-package11-retry3-usb-reducer-retest-adversarial.json)
rejected all 22 mutations. The stopped-attempt
[result](phase11-5-package11-retry3-result.json) is separately validated; its
[adversarial assessment](phase11-5-package11-retry3-adversarial.json) rejected
all 35 mutations.

## Restoration

- Fresh serial-bound inventories prove both Picos on their original boots and
  revisions, Empty, unowned, schedules disabled and output inactive.
- Pico A retains eight complete records from this attempt; Pico B retains zero.
- The held reservation was reconciled against fresh inactive inventories and
  is `RELEASED` under the Retry 3 packet hash.
- `wsprrypi.service`, both recovery timers and the original wspr4/wspr5
  management profiles are active. The temporary namespaces, units and AP are
  absent; wspr5 `wlan2` is down.
- Client, campaign and AP captures report zero kernel drops: 9,740/9,740,
  9,613/9,613 and 9,969/9,969 packets respectively.

## Remaining gate

Package 11 and R6 remain open. Before a fresh full campaign, a read-only
inventory must show the eight Retry 3 terminal records have expired. The next
packet must bind this stopped-attempt result, both adversarial assessments and
the repaired reducer evidence. It needs a new explicit physical authorization;
Retry 3 does not authorize an automatic retry.
