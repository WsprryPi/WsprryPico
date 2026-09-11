# Allocator observation cost continuation

Phase 11.5 remains OPEN. Only compile-only A1 is closed. No clock configuration
is accepted; the selected physical configuration remains 138 MHz, PIO divider 1,
with the SRAM renderer. Physical 132/150 MHz configurations remain untested.

The preserved N1s archive is `phase115-n1s-preserved-20260911.tar.gz`, SHA-256
`79850f4dd9b3eb6f97c0291e26358f4c083ced2bacd6105f0753a4f1a2aea96b`.
The private local copy is under `build/phase11-5-closure/`. It includes the failed
browser interval, completed observations and successful device/host restoration.
The earlier failed attempts and their independent artifacts remain retained.

The [linked images](phase11-5-allocator-cost-images.json) bind clean source
`8fb3894253ef45adc3aad28f25a684168487490f`, pinned SDK 2.3.1 and Arm GNU 15.3.1.
All four builds passed linked allocator routing, stack guard, flash/journal and
SRAM renderer checks. The initial local configure attempt selected Makefiles
against an existing Ninja picotool cache and failed before building; configuring
these new build directories with Ninja resolved that local build error. No
dependency was downloaded or installed for the correction.

The source repair avoids free-only heap walks and an unnecessary connection
admission status copy. It preserves allocation/reallocation peak observations,
fresh live snapshots, the reserve thresholds and all RF timing rules. The full
54-test hardware-free suite and pinned native TLS regression passed. These are
software results; the repair has not yet passed target acceptance.

The WsprryPi load runner at `16fb1fb24454f014739a7692ace0c4be66fb75b4` prioritizes
an already-due status poll over an asset or control request. Seven deterministic
tests passed. All required requests and the one-second sampling lateness limit
remain unchanged; the measured 6.013358513-second response still fails that
limit in regression. The actual production binary remains the earlier clean
`6f65d5c7d202569102459ab68d7c9ea079b96f35` artifact, not an installed replacement.

The [frozen continuation packet](phase11-5-allocator-cost-packet.json) has SHA-256
`ef96cb3f0eb19fd5a63c284120c526ffe87b72ae6136c18ff9f85da79b644e5e`.
Private root: `/home/pi/phase11-5-n1t-8fb3894`. The workload manifest SHA-256 is
`b1b1e1364bdcfca2e737c68e275ed25cc55e7529c465f71929d6b2de043dc635`;
staging archive SHA-256 is
`3bc4da76e45bf88cb7a40f8f3773cde71efa5261e787618c4a5863f28716d5c4`.
Extraction uses root ownership, protected directories and owner-only files.

This continuation uses the existing chat authorization for scoped flashing/RF,
USB reads and the isolated host fixture. Device runtime is bounded to 6,900
seconds with 600 seconds for restoration; the host fixture is bounded to 8,400
seconds plus 600 seconds cleanup. Its original absolute six-hour ceiling remains
`118796902517795` host-monotonic nanoseconds. Admission refuses to exceed it.
The preceding restored attempt contributes six configuration writes to the
unchanged cumulative cap of 32. Ordinary radios, installed services and GPSDO
settings retain the existing preservation requirements.

Before each image's matched A2 baseline, execute exactly one recorded N180
conditioning interval with the existing 240-second independent USB observer.
It must pass unchanged wire, rate, heap, stack and health checks. This records
initial allocations separately; it is not permission to condition repeatedly
until passing. Then execute Q360/controller180/N180/Q360 on that same boot.
Any failure stops dependent work. No RF job is included in this conditioning or
A2 packet. A3 retains its three ten-second 135.5 kHz Tone jobs and requires both
reviewed exact-image A2 results before admission.

The strengthened A3 audit requires all expected DMA/launch/tail counts in
addition to job-state observations. B1's three N300 repetitions are prepared but
unrun. Other matrix cases remain open. Selecting another clock during Phase
11.6 requires repeating affected Phase 11.5 checks. Phase 13 retains systematic
band × mode × clock comparison, filters, spectral qualification and release.

## A3 scheduling review before execution

The unexecuted A3 actor's twelve-second launch lead left the last RELEASE beyond
N180 in five of fifteen deterministic scheduling scenarios. The scenarios use
the actual Pi browser scheduler, three status/asset/control latency profiles and
all five integer-second USB STATUS phases. The correction uses a ten-second
lead, calculated only after the browser permit and lock are acquired. Fresh
INFO is at most two seconds old and a control request is bounded to five
seconds. All independent Loaded/Armed/Running/Complete observations remain
required; this calculation does not replace target state coverage.

Before ARM, the actor now refuses a finite job unless its launch lead, complete
duration and fifteen seconds for release/observation fit within the frozen N180
window. The offline audit also requires the entire actor lifecycle, including
its final independently observed release, inside the actual nominal interval.
Four browser-job regression methods pass, including late-ARM rejection before
any request. Against Pi driver SHA-256
`b49a89d610724e9d9224d54600b23cd0378693bd14cbccb74132c208002e9f53`,
`validate_phase11_5_a3_schedule.py` reproduces the old five failures and completes
all fifteen corrected scenarios; the latest final observation is at 164 seconds.
These are hardware-free feasibility checks, not target acceptance. A3 remains
unrun and requires reviewed exact-image A2 results and a separately hashed
helper supplement. The active A2 helpers and workload manifest are unchanged.

The follow-up adversarial assessment checked pre-ARM rejection, preservation of
all 36 browser STATUS requests and 18 assets, full-job hardware-counter coverage,
unchanged observer/state/deadline requirements, and no-access defaults. No
remaining actionable finding was identified in that bounded A3 source review.
