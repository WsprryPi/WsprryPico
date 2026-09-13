# R3 v2 B1 actual Chromium boundaries and cancellation

Reviewed under accepted R3-COMPLETE-20260913-v2 and unchanged 60 dB conducted
wiring. A only: serial 0BF4B4AEC9FFB344, device fd6127d11d6aca42a9905fa3fb1bf1d5,
source 7d183978d08d77d5de668911be041bb188c851f5, image
38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1, boot
8e777dadaa81f4618154d84de0df268a, 138 MHz/divider 1/RAM/GP2. B stays read-only.
Zero flash, reboot, Wi-Fi cycle, CONFIG save and heap probe. Preserve the installed
Pi application/service and management connectivity. Admit only from Empty,
inactive/unowned with current clock, image, observers and fixture identity.

Exactly four planned jobs, at most 452.250003 seconds charged in full before ARM:

- A real 30,000-byte valid JSON file submits one ten-second Tone at 135,500 Hz.
  A valid 30,001-byte file is attempted first and must be rejected by the real UI
  before any job POST. Both files contain the same valid job and trailing JSON
  whitespace; file size is distinguished from the reserialized request body.
- A 32-question-mark FSKCW message completes 143.250001 seconds, with 384 events.
  Dot/intra 250 ms; dash/character gap 750 ms. Mark 135,500 Hz, space 135,495 Hz.
- The same 32-character/384-event QRSS timing is owner-aborted while independently
  observed Armed. Its whole 143.250001-second plan is still charged.
- A 32-question-mark DFCW message plans 155.750001 seconds, with 384 events.
  All marks/intra gaps 350 ms, character gaps 1,050 ms; dot 135,500 Hz and dash
  135,495 Hz. Owner-abort only after at least 120 seconds of independently
  observed Running time, beyond the historical 110.592-second limit.

All message plans include a 1,000 ns final off event and are checked against the
actual source compile_message function before staging. No abort is a completed
job. Observe 31/32/33-character previews in all three modes and a spaces-included
32-character boundary without RF submission. Preserve exact duration, progress,
owner controls, terminal state, DOM snapshots, screenshots and network data.

Use existing Chromium 151 with a fresh task profile. Private NSS key/certificate
databases and a private policy/configuration copy are mounted only into the
browser's own mount namespace; the rest of the filesystem is read-only. No
global browser trust or policy changes. The target URL and certificate pin are
mandatory; no ignored certificate errors or proxy substitution. The browser
executes the target-served UI and uses actual file inputs and form/button actions.
No page source or job-control function is replaced. CDP observes request/response
bodies and guards each mutation before it reaches the target.

The guard permits only the target origin, named read-only resources and the
case's ordered HELLO/CLAIM/LOAD or LOAD_MESSAGE/ARM/ABORT/RELEASE operations.
For every new job, bind the real browser-generated session and job identity in
an atomic file before LOAD continues. Observe Loaded independently before
releasing the intercepted ARM request; retain at least five seconds of measured
start lead. Charge the full plan before releasing ARM. Never retry a mutation
with a fresh ID. A guard, browser or observer error stops further actions.
RELEASE uses the browser's own UI only when its owner is still retained; normal
lease expiry may leave an inactive, unowned Complete/Aborted record.

The declared workload is the real browser's sequential API work and normal
five-second active-job refresh, together with independent USB INFO and WTP STATUS.
No concurrent native TLS client is started for this packet. Browser asset loading
is recorded as produced, including any connection rejection. It is not relabeled
as a supported saturation pass after failure. At most 250 browser requests and
four ARM attempts. INFO starts every second, STATUS/host health every five
seconds, each observer reply within five seconds. Keep the established 32 KiB
heap/4 KiB stack reserves, zero faults and 2,849,391 ns RF service budget.

Execution is bounded to 900 seconds plus 150 seconds final observation/cleanup.
The whole budget must fit before F0's unchanged 290477130169000 ns monotonic
cleanup deadline. Only task-owned Chromium/namespace processes are stopped.
On producer failure, independent readers continue to the original finite deadline;
final inactivity requires authoritative observations, never process exit alone.
Capture final A/B identity/configuration/authority. Retained records are preserved.

Independently audit raw browser and USB evidence and inspect rendered outcomes
before scoring. Preserve passing assertions even if another case fails. This
packet can cover real browser file admission, message UI and selected lifecycle
paths; it is not a native Pi submission or one-hour completion qualification.

- `packet_sha256`: `7b0de46064c8379400a2dc6b937ab5e32b64fe750c15bb18ca2692d8fa10c4f6`
- `archive_sha256`: `4f272a1c327a64ea0f5fd3734f885259f2c5f0dde5d227ab0142b4474489cd33`
- `root`: `/home/pi/phase11-5-r3-v2-browser-b1-20260913`
- `stager_sha256`: `f57ef410257725aa2c3bbd1e5333f2ffe8232ba94835ee705dbeb159d7e44690`
- `observer_sha256`: `f54142a010a89d7c2a98ede96db01472e63263bf4e61a1aa20e3b8af0b906de1`
- `producer_sha256`: `56a27e9f37f7791777fc8ada8cf24a2ede6f3cfb79b5cda642ff798c05705f04`
- `guard_sha256`: `0b685c30c41a86b9c825a4754ef852a11e627b2151211f96b28c53406b6eb218`
- `planned_jobs`: `4`
- `rf_duration_ns_charged_maximum`: `452250003000`
