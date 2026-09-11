# Phase 11.5 P1 continuation after host-only repair

Status: EXECUTED AND FAILED; one job submitted, no retry.
See [the preserved result](phase11-5-pilot-attempt2.json). The following records
the original continuation scope, not authority to repeat it.
The original P1 authorization remains the hardware scope: exactly three finite
10-second 135.5 kHz Tone jobs on Pico A at 138 MHz, the same candidate and guarded
restoration, unchanged RF path and no other device/service/radio changes.

[P1](phase11-5-pilot.md) stopped before BOOTSEL or any job. Both original boots
and explicit inactive, empty, unowned states were freshly reconciled. This
continuation repairs only the host evidence reader; it does not retry a submitted
job, recover a device fault, reboot an unknown-output board or broaden any limit.
All original stop rules, operation counts, finite jobs and 17-minute unit bound
remain unchanged. Preserve the failed original unit and evidence directory.

The [revised packet](phase11-5-pilot-revised.json) retains the same three job IDs,
firmware source ce1c339a976e795e90c38c4a57578f9c8ed75615 and UF2 SHA-256
b9af965a012e1dcbad6310b36285fe386a89218ccf2fe9c263afaf84bfec356c.
Only the supervisor hash changes; helper source is 00d26a3c6f7a4dfcee9116848c6bb6b86193ee9b.
Packet SHA-256: `2ce6fc5e63b835efe120f3dd8c106d6e6a3a0d211fcddd44a7584e2886c8dd7d`.

Use new private directory `/tmp/phase11-5-p1b-ce1c339` and new transient unit
`phase11-5-p1b-ce1c339`. Substitute that directory/unit in the original prepared
command; the same ExecStopPost is armed before ExecStart. Validate all hashes
and absent evidence/unit before execution. No firmware rebuild is involved.

Four supervisor and six pilot regressions passed. The repaired reader accepted
the real successful inventory and rejected both real failed stage logs. WTP
wire integer validation remains unchanged. The original failure remains in
[its attempt record](phase11-5-pilot-attempt1.json). No physical clock acceptance
is claimed by this repair or the eventual finite pilot.
