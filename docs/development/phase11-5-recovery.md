# Phase 11.5 fault restoration packet

Status: READY FOR SEPARATE AUTHORIZATION; not executed.
Restore the original inhibited firmware after preserving the failed P1b evidence.
Do not resume the campaign or submit either remaining RF job.

DUT: Pico A USB 0BF4B4AEC9FFB344, WTP fd6127d11d6aca42a9905fa3fb1bf1d5,
current firmware ce1c339a976e at 138 MHz, boot dd156859a9a87dc6d0fcd161bb30518d.
Require exact retained job ec30945b745c408d950b46d48f0cbd38 in Failed with
DEVICE_FAULT, explicit output false, no owner, healthy storage and disabled
autonomous schedules. Require unchanged original station, schedule, watermark
and network identity settings. Protect and read Pico B by its serial/full ID;
require its original revision and boot.

Use the existing guarded Console BOOTSEL reset path. Source review confirms
Scheduler::reset_permitted admits a latched failed state only with no owner,
no active output, healthy storage and disabled schedules; the Console also
requires successful engine disable. This reset is fault recovery, not an idle
management operation and not a restart of the RF pilot.

Perform exactly one serial-specific `picotool load -v -x` of the original
inhibited UF2 SHA-256
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`,
using the existing checked picotool. No erase-all, journal erasure, debugger,
OTP write, ABORT, RELEASE, new job or RF output. Read both boards after loading;
require A's original 802c91a7b86e-dirty inhibited image, empty/unowned/inactive
state and preserved configuration; B must remain unchanged and inactive.
Stop on any unexpected response. No retries or fallback flashing.

Helper: scripts/phase11_5_recover.py, SHA-256 `2b806e11030867c0187a319b7116a97c81800bca4e979fcb3e89de8c9cd635ec`.
Five supervisor/recovery tests passed, including active-output, owner, wrong
boot/job/clock and enabled-schedule rejection. Its admission predicate also
matched the actual preserved reconciliation. Local default validation accepted
the restoration image and prior baseline without hardware access. Automatic
approval review rejected remote staging/default validation; it interpreted the
helper as able to flash despite omission of --run. No recovery helper was
executed remotely.

Proposed new unit: phase11-5-p1-recovery, Type=exec, Restart=no,
RuntimeMaxSec=420, TimeoutStopSec=30, UMask=0077. It runs independently of SSH
and has at most 7.5 minutes including forced shutdown. No existing unit, radio,
route, GPSDO output or installed transmitter is changed. Preserve both failed
pilot units, raw evidence, backup and failure state records.

After authorization, stage this exact helper in the existing private bundle and
verify its hash. ExecStart is:

`/usr/bin/python3 /tmp/phase11-5-p1b-ce1c339/scripts/phase11_5_recover.py --restoration /tmp/phase11-5-p1b-ce1c339/restoration.uf2 --prior /tmp/phase11-5-p1b-ce1c339/evidence --evidence /tmp/phase11-5-p1b-ce1c339/recovery --run`

A new empty evidence directory is mandatory. Unlike the campaign supervisor,
this recovery unit is itself the single bounded restoration action; another
restoration is never triggered after its failure. Successful restoration does
not pass or erase the failed physical resource/deadline result.
