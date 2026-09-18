# Phase 11.5 Package 11 Retry 3 preflight review

## Scope

This review prepares Retry 3 after Retry 2 stopped before reservation on the
unchanged memory-headroom gate. It does not authorize or execute Retry 3 and
adds no R6 credit. Phase 11.5 remains open at five of six families.

## Repair

The retained-terminal gate is separate from the accepted workload and resource
criteria. It uses fresh, serial-bound, read-only USB inventories after the
installed WsprryPi service is paused. It accepts only the frozen Pico A identity,
unchanged boot, no owner, inactive output, disabled schedules and zero to eight
unique complete/output-inactive terminal records. A packet-bound set of unique
administrative sessions supports at most 600 seconds of 15-second polling.

The runner rejects a record whose calculated remaining one-hour lifetime is
outside that authorized wait. It must observe an empty terminal set before it
starts the existing 360-second memory gate. The 165,000-byte preflight
threshold, 1,024-byte R6 resource-return limit, replay retention, firmware,
workload and RF budget remain unchanged.

## Adversarial review and repairs

The first repair pass added the bounded terminal-retirement wait. The source
review then found two missing rejection details: duplicate terminal identities
could pass the structural check, and a record with more than 600 seconds left
could consume the whole wait even though the attempt could not succeed within
scope. The runner now rejects both cases. It also rejects failed, missed,
aborted or output-active records rather than aging them into an apparently
clean preflight.

Changing the fixture authorization changed its source hash, so the prior
credential-owner retest was no longer applicable. The second wspr5 Linux
host-only retest passed against the exact current fixture source. It used six
synthetic files and performed no Pico, USB, network, service, reservation or RF
action.

## Reassessment

- Package 11's focused suite passes 20/20, including retirement-to-zero,
  unsafe-record rejection, Retry 2 dependency binding, cumulative accounting,
  credential applicability and Retry 3 authorization.
- The Retry 2 stopped-attempt assessment rejects 32/32 mutations and the
  intact result validates again.
- The synthetic final-closure assessment rejects 58/58 mutations, including
  Retry 2 preservation, zero Retry 2 charge, retention-preflight credit and
  both Retry 2 dependency hashes.
- The admission assessment rejects 26/26 mutations and the Retry 1 assessment
  rejects 31/31.
- Python syntax checks and `git diff --check` pass. The complete documented host
  suite passes 81/81.

The separately authorized Retry 3 packet is the next physical action. A stopped
or failed Retry 3 requires another evidence-bound authorization.
