# Phase 15 list and saved/pending prompt index

Updated 2026-10-17. This is the saved full list requested when inserting GPIO
drive strength. The [implementation plan](../implementation-plan.md#phase-15-operator-review-punchlist)
is authoritative for detailed acceptance and later status updates. Update this
index when the current sequence or prompt paths change. Historical closures
retain their evidence and limitations.

## Current list

Fifteen items are complete within their recorded scopes; five have not started.
P15.14 USB closure was supplied by the
concurrent USB task and is preserved here; this planning task did not execute
or requalify USB control. Four unexecuted numbered prompts (P15.16–P15.19)
are saved; preparing those documents does not execute the tasks.

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
| P15.14 | USB control | Complete | [USB execution record](usb-control-results.md); [100 ms UTC follow-up prompt](utc-100ms-execution-prompt.md) and [results](utc-100ms-results.md) |
| P15.15 | GPIO drive-strength configuration across Pico and WsprryPi | Complete within recorded scope; nonblocking RF observations retained | [Prompt](phase15-15-execution-prompt.md), [software record](phase15-15-results.md), [hardware prompt](phase15-15-hardware-execution-prompt.md) and [acceptance](phase15-15-hardware-results.md) |
| P15.16 | Make the default firmware build uninhibited | Not started | [Saved default-build prompt](phase15-16-execution-prompt.md) |
| P15.17 | Publish a GitHub testing prerelease with a firmware asset | Not started | [Saved testing-prerelease prompt](phase15-17-execution-prompt.md) |
| P15.18 | Installer | Not started | [Saved USB-installer prompt](phase15-18-execution-prompt.md) |
| P15.19 | Impeccable review of the web UI, including provisioning | Not started | [Saved Impeccable UI-review prompt](phase15-19-execution-prompt.md) |
| P15.20 | Create user documentation for Read the Docs Community | Not started | No standalone execution prompt saved |

## Renumbering and dependency map

| Previous current number | New number | Task and prompt action |
| --- | --- | --- |
| P15.1–P15.18 | Unchanged | Preserve task identities, saved prompt paths and historical evidence. |
| New insertion | P15.19 | Impeccable web UI review, including provisioning; [execution prompt saved](phase15-19-execution-prompt.md). |
| P15.19 | P15.20 | Read the Docs Community user documentation; no standalone execution prompt saved. |

The earlier GPIO insertion established the current P15.15–P15.18 sequence
and moved the default-build handoff to `phase15-16-execution-prompt.md`.
The saved, unexecuted prompts now use P15.20 for operator documentation and
leave the separate P15.19 UI review for execution after Installer acceptance.

Execution order after accepted USB control is **P15.15 → P15.16 → P15.17 →
P15.18 → P15.19 → P15.20**. P15.16 must preserve accepted GPIO-drive behavior. The
prerelease, installer and final user documentation must include that setting
and its compatibility/qualification limits. P15.19 reviews the delivered web UI,
including provisioning, before P15.20 finalizes instructions and screenshots.
The default-build prompt retains
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
The new drive-strength handoff is additional. The subsequent
[P15.17 testing-prerelease prompt](phase15-17-execution-prompt.md) is also saved
for execution after P15.14–P15.16 acceptance; preparation publishes nothing.
The [P15.18 USB-installer prompt](phase15-18-execution-prompt.md) is saved for
execution after P15.14–P15.17 acceptance, including independent review,
repair/retest/reassessment and scoped commit/push instructions. Preparation
does not execute it. The [P15.19 Impeccable review prompt](phase15-19-execution-prompt.md)
is saved with the existing-interface Improve/Check flow, reusable Pi startup
context and Pico's lightweight/familiarity requirements. Preparation does not
run the review. P15.20 has no standalone execution prompt saved.
Discussion and checklist entries are not evidence of implementation.

Original executed prompts, results, frozen plans, source manifests, historical
P15.14 operator-documentation references, commit identities and external Pi
checklists retain their original numbering. Current references in the
implementation plan, development index and unexecuted prompts use P15.20 for
operator docs. This avoids changing the meaning of old evidence merely to match
today's order.
The new prompt's [adversarial preparation assessment](phase15-15-prompt-review.md)
records findings, repairs, reassessment and documentation checks.
