# Component 9: bounded Pico LOAD replay validation under TLS pressure

The user requested this prompt and its execution on 2026-09-15, including
adversarial review, repair/reassessment, commit and push. Use the new bounded
period below; previous failed attempts and their exhausted allowances remain
historical evidence.

Validate clean source `98f5797d77fb2bc4c11a4e80f6ff35d7ad16a5b5` on Pico A,
serial `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`.
Board is Pico 2 W / RP2350 Arm, 138 MHz GP2 PIO/DMA, RAM renderer. Pico B,
serial `CDDBF8767C506C07`, is read-only. Preserve configuration, physical RF
setup and the installed WsprryPi application.

Build and identify the clean candidate with local SDK 2.3.1 and GCC 15.3.1.
Verify linked allocator, stack-guard and renderer checks and UF2 application
boundaries. Freeze the image, helper and request hashes before any deployment.

* ELF SHA-256: `ff594d831ef3e98d0ac3e062260d7c2ed8c9b81ab206eff7c941230b96b85f71`.
* UF2 SHA-256: `b6d5ab7610a0e19e9de91ce78dde4eb7c63b9192343dd86af4f7bcb857838733`.
* Packet SHA-256: `901dd35c54ca3866068c8e9c68b89e7985b8bcdc2eb52cb5577464b8099f8f85`.
* Private root: `/home/pi/phase11-5-r3-v2-load-reply-c11-20260915`.

Use one new one-hour hardware period from the first host clock/preflight, with
the final 15 minutes reserved for cleanup. Freeze UTC and host-monotonic deadlines
in the packet and do not restart either deadline. Permit exactly one
serial-specific BOOTSEL command and one verified candidate flash, one E6
preparation LOAD followed by ABORT/RELEASE and at least 310 seconds of cache
aging, one primary LOAD and two conditional replays. Permit no ARM, RF output,
Pico configuration write, extra reboot, Wi-Fi recovery cycle or automatic retry.
Preserve the installed candidate afterward.

Verify fresh A/B identity, inactivity, ownership, scheduling and configuration
before deployment. Expected A before deployment is source `e256633304e0`, boot
`11dac3985326cb81c49022efcdceb5d4`. Its historical reserve excursion is already
recorded and must not be relabeled. After the flash, require the exact new source,
a changed boot, unchanged configuration and all candidate resource gates.

Establish the existing temporary network fixture with independent timed cleanup,
retained credentials and preserved management connectivity. Require two healthy
INFO samples with link 3, address 10.77.15.10 and the listener ready before opening
the authenticated TLS observer. The fixture uses 1,200 seconds of runtime and
600 seconds of restoration, bounded by the absolute deadline.

Send the exact 52,105-byte C7 primary frame, SHA-256
`e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
Only after its success send one byte-identical replay and one same-job request
with the frozen fresh request ID. Each exchange must finish within five seconds,
including writes, with complete framing, CRC, schema, identity and all 512 exact
adjustments in the 54,916-byte response payload. Replay replies must match the
primary apart from the fresh request ID. Verify Loaded/inactive ownership before
ABORT/RELEASE.

Maintain the existing 90-second authenticated TLS STATUS observer, four HTTPS
status reads spaced by at least 20 seconds and independent single-flight INFO
sampling near 1 Hz, starting at least 30 seconds before LOAD and ending at least
30 seconds afterward. Audit TLS allocation samples bracketing each of the three
exchanges against the recorded 31,384-byte cost. Require at least 32,768 bytes
of allocator headroom, valid stack guards and reserves, and zero allocation
failures, faults or RF activity. Do not relax thresholds or add workload to
manufacture comparability.

Stop dependent work on the first unexpected failure. Reconcile A to
Empty/inactive/unowned, verify B unchanged, and independently verify fixture,
protected host state and configuration restoration within the fixed deadline.
Preserve failed attempts and incomplete responses. Do not infer output state
from connection closure or missing acknowledgments.

Independently audit raw request/reply bytes, actual writes, deadlines, retained
state, TLS/HTTPS and INFO evidence, final authority and restoration. Test altered
evidence rejection, repair actionable tooling findings offline and reassess.
Award only the bounded LOAD/replay acceptance supported by observations; broader
Group 2 remains separate. Save this prompt, identities, results and review in
the repository; keep captures, credentials and generated images private. Commit
and push, independently verify remote parity, and report the acceptance state
and remaining work.
