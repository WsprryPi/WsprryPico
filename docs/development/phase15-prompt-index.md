# Phase 15 list and saved/pending prompt index

Updated 2026-10-17. This is the saved full list requested when inserting GPIO
drive strength. The [implementation plan](../implementation-plan.md#phase-15-operator-review-punchlist)
is authoritative for detailed acceptance and later status updates. Update this
index when the current sequence or prompt paths change. Historical closures
retain their evidence and limitations.

## Current list

Fourteen items are complete; five have not started. P15.14 USB closure was supplied by the
concurrent USB task and is preserved here; this planning task did not execute
or requalify USB control. Neither saved future prompt has been executed.

| Item | Task | Status | Saved prompt or current handoff |
| --- | --- | --- | --- |
| P15.1 | Preserve Pico configuration across legacy and partial updates | Complete | [Original issue handoff](issue447-execution-prompt.md) |
| P15.2 | Use compatible Pico configuration updates and verify supported version pairs | Complete | Pi-led; no current Pico execution prompt |
| P15.3 | Define and implement supported management carriers | Complete | [Execution record](phase15-3-management-carriers.md) |
| P15.4 | Adopt shared application, station and hardware resources | Complete | [Original shared-application handoff](shared-transmitter-application-execution-prompt.md) |
| P15.5 | Add multi-threaded web service | Complete | [Original executed handoff](phase15-5-execution-prompt.md) |
| P15.6 | Support multiple simultaneous login sessions (software scope) | Complete | [Original executed handoff](phase15-6-execution-prompt.md) |
| P15.7 | Recover login cleanly after a failed save or lost session (software scope) | Complete | [Original executed handoff](phase15-7-execution-prompt.md) |
| P15.8 | Add WSPR Type 2/3 to WsprryPico | Complete | [Original executed handoff](phase15-8-execution-prompt.md) |
| P15.9 | Save valid fields independently of transmit readiness | Complete | [Original executed handoff](phase15-9-execution-prompt.md) |
| P15.10 | Allow hostname changes and use the hostname in the page title | Complete | [Original executed handoff](phase15-10-execution-prompt.md) |
| P15.11 | Consolidate or split Station/Transmission and Wi-Fi/Host setup | Complete | [Original executed handoff](phase15-11-execution-prompt.md) |
| P15.12 | Show the hostname as the main-page identity | Complete | [Original executed handoff](phase15-12-execution-prompt.md) |
| P15.13 | Complete untested-band qualification and resolve clock-dependent support | Complete | [Frozen qualification plan](phase15-13-plan.md) |
| P15.14 | USB control | Complete | [USB execution record](usb-control-results.md) |
| P15.15 | GPIO drive-strength configuration across Pico and WsprryPi | Not started | [Saved drive-strength prompt](phase15-15-execution-prompt.md) |
| P15.16 | Make the default firmware build uninhibited | Not started | [Saved default-build prompt](phase15-16-execution-prompt.md) |
| P15.17 | Publish a GitHub testing prerelease with a firmware asset | Not started | No standalone execution prompt saved |
| P15.18 | Installer | Not started | No standalone execution prompt saved |
| P15.19 | Create user documentation for Read the Docs Community | Not started | No standalone execution prompt saved |

## Renumbering and dependency map

| Previous current number | New number | Task and prompt action |
| --- | --- | --- |
| P15.1–P15.14 | Unchanged | Preserve completed work and historical evidence. |
| New insertion | P15.15 | GPIO drive strength; saved as `phase15-15-execution-prompt.md`. |
| P15.15 | P15.16 | Uninhibited default build; saved handoff moved to `phase15-16-execution-prompt.md`. |
| P15.16 | P15.17 | GitHub testing prerelease; checklist requirements retained, no separate saved prompt found. |
| P15.17 | P15.18 | Installer; discussion remains in "Assess WsprryPico installer options", no installer execution prompt found. |
| P15.18 | P15.19 | Read the Docs Community user documentation; checklist/handoffs retained, no separate saved prompt found. |

Execution order after accepted USB control is **P15.15 → P15.16 → P15.17 →
P15.18 → P15.19**. P15.16 must preserve accepted GPIO-drive behavior. The
prerelease, installer and final user documentation must include that setting
and its compatibility/qualification limits. The default-build prompt retains
its previously requested independent review, repair/retest/reassessment and
commit/push instructions for its later invocation. They do not authorize work
or Git operations while preparing this index or the new P15.15 prompt.

The previous `phase15-15-execution-prompt.md` URL/path now resolves to a different
task. An older pasted prompt remains historical text; it cannot be rewritten in
another chat. Check both title and number before invoking it. Use
[the renamed P15.16 file](phase15-16-execution-prompt.md) for the default build.
No existing chat was messaged, retitled or otherwise changed by this update.

## Saved/pending inventory and historical records

The repository and the recent "Assess WsprryPico installer options" / "Pico
Release Checklist" handoffs were inspected. The only saved, unexecuted Phase 15
numbered execution prompt before insertion was the default-build handoff.
The new drive-strength handoff is additional. Discussion and checklist entries
are not execution authorization or evidence of implementation.

Original executed prompts, results, frozen plans, source manifests, historical
P15.14 operator-documentation references, commit identities and external Pi
checklists retain their original numbering. Current references in the
implementation plan and development index use P15.19 for operator docs. This
avoids changing the meaning of old evidence merely to match today's order.
The new prompt's [adversarial preparation assessment](phase15-15-prompt-review.md)
records findings, repairs, reassessment and documentation checks.
