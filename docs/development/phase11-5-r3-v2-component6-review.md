# Component 6: observer repaired; network recovery blocks LOAD validation

The corrected observer is fixed and tested. The pending primary LOAD still did
not run: Pico A could not obtain an address after the temporary AP was restored.
No new Group 2 assertion closes. The existing repaired firmware remains installed;
no flash, preparation LOAD, primary LOAD, replay, RF job or Pico Wi-Fi command
occurred in this continuation.

The [scope](phase11-5-r3-v2-component6-scope.md) records the user's “Fix it”
authorization and the unchanged one-hour limit. The
[result](phase11-5-r3-v2-component6-result.json) preserves both prerequisite
outcomes, exact packet/source identities, evidence hashes and final state.

## Execution and finding

Fresh read-only admission verified A's exact `e256633304e0` image and boot
`11dac3985326cb81c49022efcdceb5d4`, unchanged configuration and the original E6
Aborted record. The preparation response and cache aging were reused from C8's
raw audited evidence. B's image, boot and configuration were unchanged.
A first command-line preflight rejected an incorrectly sized session ID before
opening the device; the subsequent inventory used a generated valid identifier.

C9's TLS socket received `No route to host` before any primary LOAD. Review found
that host/client fixture readiness had incorrectly been treated as proof that
the Pico had rejoined. The fixture and both devices were restored. The corrected
C9a prerequisite kept the original start and both deadlines, with the still-unused
single primary and conditional replay allowance. C9's failed trace is preserved
under `prerequisite/`, separately from C8's retained-preparation evidence.

The new gate read 43 complete INFO replies. Link status alternated between 1
(joining) and -3; the address remained empty. The pinned SDK 2.3.1 CYW43 header
maps -3 to `CYW43_LINK_BADAUTH`. The fixture's retained and active credential-file
hashes both match C8's successful setup:
`fc42b65f177e62afc6664ffc1f13bc14e7711d7cd51c9d191c2e0c580d620764`.
A contemporaneous host station read reported Pico A associated and authenticated,
but firmware had no IP and DHCP recorded no successful Pico exchange. These
observations do not establish a wrong password or the firmware branch causing
the failure. No credentials were changed or published.

The gate stopped before opening TLS or sending LOAD. All observed allocator and
TLS allocation-failure counters remained zero; allocator peak stayed at 112,920
bytes. This does not exercise the repaired LOAD under TLS pressure. C8's observer
failure and C9's premature connection remain historical failures, not rewritten
passes.

## Repairs and adversarial reassessment

* Added a no-flash admission mode requiring the retained firmware, boot,
  configuration and exact E6 record. Its packet rejects any flash/BOOTSEL allowance,
  and the deployment entry point rejects this scope.
* Required a healthy first INFO sample before the 30-second observation prelude.
* Added a bounded network gate requiring two consecutive healthy samples with
  link status 3, address 10.77.15.10 and a listening control service. A regression
  includes a ready/not-ready transition to verify that consecutive observations
  are required.
* Raw readiness and retained/prerequisite evidence are independently reconstructed.
  The auditor verifies unchanged deadlines and zero previously consumed primary
  or replay requests before assessing a continuation.
* Review found that the two-second readiness sleep could overrun its nominal
  deadline. The original failed trace lasted 91.231 seconds; it remains recorded.
  The sleep now clamps to the remaining time, with an explicit half-second-boundary
  regression. This host-only correction was not used to repeat physical work.

Ten runner cases pass. The prior C8 evidence suite still rejects all 15 altered
cases. The new continuation suite rejects eight changes covering readiness without
an address, raw/summary disagreement, an undeclared command, sequence corruption,
previous primary use, deadline extension, extra flash and final output authority.
Six affected CTest targets pass. Reassessment found no remaining actionable defect
in these host corrections or the stopped-run evidence. Successful physical
LOAD/replay and sustained TLS/HTTPS observation remain unperformed.

Reproduce the offline continuation check with:

```sh
python3 tests/phase11_5_load_reply_continuation_audit_tests.py \
  --evidence build/phase11-5-r3-group2-component6/evidence
```

Firmware source, RF code, protocol and memory reserves are unchanged. Generated
firmware, credentials and raw captures remain private; published evidence is
summaries and hashes.

## Restoration and proposed recovery

Independent verification finished 1,033.433 seconds after the original period
start. Both fixture instances were restored. Final A/B inventories report Empty,
inactive, unowned and scheduling disabled with unchanged configuration. A retains
boot `11dac3985326cb81c49022efcdceb5d4`; B retains source `8921a7008183`, boot
`6684b4b197d80cfa0ce83b3aaf205cb0`. Installed WsprryPi PID 1957 and its executable
hash are unchanged. Protected host files/services, management addresses, radios,
recovery timer and absence of temporary resources were independently verified.

The next proposed device action is exactly one idle Console `WIFI OFF` followed
by `WIFI ON` on Pico A, with raw acknowledgments, INFO checks and guaranteed ON
cleanup. Preserve firmware, boot, saved settings and RF inactivity. Then require
successful address/time/TLS readiness before the still-pending primary LOAD and
two conditional replay checks. This recovery is not a firmware-fix acceptance
result. The executed scope explicitly permits zero Pico Wi-Fi cycles, so that
additional action is pending user authorization. If the retained E6 record has
expired, a fresh single preparation LOAD and cache-aging interval must be included
in the continuation scope rather than pretending the old record still exists.
