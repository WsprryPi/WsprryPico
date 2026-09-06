# Step 9 standalone RF and wall-power execution prompt

Work directly in `devel` to complete Phase 9's remaining standalone RF and
wall-power validation on the existing Pico 2 W and conducted GP2/GND → 60 dB
attenuation → wspr5 RSP1B setup. The user's new request resumes the work deferred
in the preceding Wi-Fi-only turn.

Read project instructions, contracts, architecture, development procedures and
prior Wi-Fi/RF evidence. Preserve unrelated work. Refresh `devel`, identify the
connected board and installed firmware, and verify receiver availability,
capture-helper identity, storage capacity and other signal-source states. Keep
credentials private. Use the established station identity, Wi-Fi configuration,
selected pool.ntp.org address and 500 ms UTC uncertainty budget.

Build and inspect the explicitly classified standalone RF image and RF-inhibited
recovery image. Record exact source and image identities. Review persistence,
schedule expiry, local STOP, startup, watchdog recovery, time aging and RF/Wi-Fi
resource coexistence before enabling a schedule. Repair actionable defects and
rerun affected checks.

Provision a finite campaign whose complete frames fit before expiry. First
verify RF-image identity and inactive output with scheduling disabled. Then
enable a bounded schedule and collect a complete conducted frame without USB
time-setting, LOAD, ARM or per-symbol commands. Verify capture identity,
completeness, count, hash, overflow/clipping and receiver cleanup. Independently
decode the expected station message.

After a successful baseline, coordinate a real power interruption and transfer
to a suitable USB wall adapter, leaving the conducted RF path unchanged. Confirm
the Pico is absent from the Mac's USB inventory. Capture and independently
decode repeated locally scheduled frames with no USB host connection. Retain
operator-confirmed transfer times. Distinguish receiver wall-clock estimates from
calibrated RF onset measurements.

Reconnect to the Mac at the instructed point. Verify persisted configuration,
boot identity, schedule watermark, terminal diagnostics where available and
inactive output. Confirm missed or previously reserved occurrences are not
replayed. Retain failed attempts and qualify only the exact tested image/setup.

Stop local execution, persist scheduling disabled and restore the RF-inhibited
image. Verify final device and receiver states. Do not leave an indefinite RF
schedule or background capture running.

Perform an adversarial review of implementation, tooling, raw evidence and
completion claims. Fix actionable findings, rerun affected validation and
reassess. Mark Phase 9 complete only if its required physical evidence passes.
Keep calibrated timing, filters, spectrum, endurance, destructive brownout tests
and broader release qualification separate.

Record sanitized results and update the roadmap to match observed evidence.
Commit only attributable changes, push `devel`, verify clean status and upstream
equality, and report results, limitations, exact commit and final device state.
