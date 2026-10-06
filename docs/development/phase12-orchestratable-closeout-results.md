# Phase 12 orchestratable closeout continuation

Status: **DECLARED AUTOMATIC WORK COMPLETE**. All four requested automatic
workstreams are closed within their independently reviewed scopes on `devel`.
Phase 12 remains `OPEN_PARTIAL` for operator-dependent and broader qualification
work. Original stopped runner results are retained; scoped acceptance uses the
complete original evidence and independent assessments.
The execution direction is in
[the closeout prompt](phase12-orchestratable-closeout-prompt.md).

## Completed in this continuation

- Corrected HTTPS authority formatting in the maintained network and
  composition clients: default port 443 is omitted consistently; nondefault
  ports remain explicit. Browser requests and resource-pressure requests now
  use the same authority.
- Added the optional intended-device selector to the native fixture while
  preserving its B default. Reset-intent preparation now supports the existing
  production capacity of one through four bonded peers and preserves their
  nonintent access bytes. It no longer requires deleting valid peers to fit
  a single-peer fixture assumption.
- Reused validated BlueZ characteristic proxies within each live connection.
  Reconnect and close retire the cache. Acknowledged write framing, fragments
  and protocol limits remain unchanged. The repeated upload acknowledged
  832 bytes within the preparation attempt, compared with 512 previously;
  neither attempt completed the required 1,993-byte upload.
- Added the AP netif's up flag, link flag and IPv4 address to `INFO`. This is
  an observation; it does not change AP lifecycle or network routing.
- Built the single consumer diagnostic candidate from reviewed commit
  `133ca93cc2a14a6cc0414ab393275f66259ac309`, Pico SDK 2.3.1 at
  `079c6f39023649b154152db30f1d781e884879bc` and GNU Arm 15.3.1. Existing
  picotool and pioasm helpers were imported. The firmware build installed no
  dependencies and compiled no native Mac helper.
- Loaded that diagnostic application onto A. All 7,119 application pages
  matched the built ELF; the reserved 53,248 bytes and E10 were preserved.
  A reports revision `133ca93cc2a1` and the new boot identity. The separate
  one-Save/STATUS measurement and its cold preservation check below now pass.
- Completed one supported engineering station Save and cold persistence check
  on B: configuration generation 2 to 3, profile generation 2 preserved,
  new boot observed, saved station/pins and unrelated settings retained,
  followed by authenticated TLS-WTP ownership acquisition and release.
  The earlier four accepted API saves were not replayed.
- Completed a fresh wspr4 BLE Pair, encrypted GATT identity/password exchange
  and WTP HELLO against the same B boot. The controller supports Secure
  Connections with a 16-byte encryption key; this does not claim MITM
  authentication. wspr4 provides an automatic BLE peer without phone action.
- Captured B's current checkpoint and independently compared its two retained
  peers with BTstack and the unchanged wspr4 host key. Both peers and the
  original E10 were preserved; no flash write or baseline restoration was
  performed. This supplies the prerequisite for the journal/reset tests.
- Added the existing BLE client's required `python3-dbus` and `python3-gi`
  runtimes on wspr4, with three required supporting packages. No existing
  package was upgraded or removed. Imports now pass, allowing the BLE client
  to run beside its controller instead of forwarding each fragment's D-Bus
  call through the Mac.
- Completed the first controller-local BLE health check in 14.2 seconds.
  wspr4 performed the existing client's fragments locally; B returned the
  expected generation and boot in HELLO/STATUS, with null owner and job.
  No Pair, profile apply or job was issued. The worker exited, its new relay
  retired cleanly, and B's after-INFO showed the same boot and zero BLE
  connections. This qualified the health path. The later complete resource
  proof is recorded below.
- Corrected the maintained BLE client's exchange deadline to cover both
  synchronous fragment writes and the reply wait. BlueZ's write timeout uses
  the remaining deadline; recording adapters still observe the original
  acknowledged frames. Four behavioral controls fail against the previous
  source and pass with the correction. Existing case limits are preserved.
- Completed A's ordinary one-Save/STATUS overlap measurement after refreshing
  its observer association once inside the existing claim window. The single
  Save and all 20 STATUS requests succeeded. Two actual request intervals
  overlapped the Save; the target trace recorded one erase and 18 programs,
  with STATUS spans outside the flash append. Public readback reported durable
  profile generation 3 while the warm runtime retained generation 2. The case
  completed in 140 seconds with clean cleanup, no firmware load and no baseline
  restoration. The subsequent cold observations and snapshot now independently
  verify profile generation 3 with the requested station value, unchanged
  standalone records, trust material, cursor, watermark and E10. The runner
  stopped while passing native stdout bytes to its JSON reporter; the complete
  snapshot and successful native output were already retained. Independent
  assessment uses those originals, preserves the stopped-run result and
  requires no repeated snapshot or Save. A private successor corrects that
  reporter and passes normal and optimized offline checks against the actual
  native stdout; it performs no additional device operation.
- Closed the declared automatic B12J credential-journal scope after independent
  original-data review. Prior cases 0 and 8 were retained; new cases 9 and 10
  preserved B/generation 3 and committed C/generation 4 respectively. Fresh
  TLS checks admitted the selected credential and refused the other two.
  Corruption cases and healthy-C recovery pass, with exact access records,
  both peers, operational records, cursor/watermark and E10 preservation.
  No Pair, time submission or accepted-case replay occurred in this tranche.
  Stale-time datagrams and arbitrary physical cuts gain no new credit.
- Completed the supported reset's state transition: both bonds were cleared,
  with the intended effective configuration, cursor/watermark and E10 intact.
  Its configuration counter advanced from 3 to 5 through the production
  save-and-purge path. Independent packet review proves cryptographic old-peer refusal: two
  retained-key encryption attempts returned PIN_OR_KEY_MISSING before local
  disconnect. The original helper's INCONCLUSIVE result is retained. No SMP
  pairing traffic was captured; post-attempt flash equals the reset snapshot.
  The declared automatic R11P reset/old-peer scope is closed. One subsequent
  supported Pair uploaded the exact 1,993-byte C profile and received its
  generation-2 apply acknowledgment. The runner stopped on the first USB INFO
  during reboot re-enumeration; its STOP and cleanup failure remain recorded.
  A later fresh readback independently confirms current C boot, synchronized
  station connection, listening control and quiet simulator state. This readback
  supplies current resource context, not a complete warm-loop pass.
- Completed the existing BLE and TLS empty-owner disconnect/lease assertions.
  Each carrier made exactly one five-second CLAIM and disconnected without
  RELEASE or a job. Independent CRC-frame review confirms that USB observed
  the same owner before disconnect, then null ownership after 1.394 seconds
  for BLE and 4.903 seconds for TLS, within seven seconds. Boot, profile,
  operational values and flash counters were unchanged; final authority was
  empty and inactive with zero BLE/network connections. The owned worker,
  relay and sockets are retired. This closes the declared two-carrier lease
  subset, not whole composition or physical peer pressure.
- Completed the original maximum inbound BLE WTP framing assertion. Native
  originals contain the exact 65,536-byte padded STATUS payload, valid CRC and
  all 1,025 acknowledged ATT segments, followed by its correlated response.
  The transfer took 107.324 seconds inside its measured finite 180-second bulk
  allowance; each write and the reply retained five-second limits. One
  65,537-byte length header received INVALID_FRAME, then final STATUS succeeded
  on the same connection. Independent review confirms one Connect, no Pair,
  CLAIM, LOAD, jobs or durable writes, unchanged boot/profile/access/settings
  and flash counters, and final empty, inactive authority. The owned lane is
  retired. This closes inbound maximum-framing coverage without claiming a
  maximum-size outbound response or whole composition/resource acceptance.
- Applied the operator's specific approval to remove the persistent SNTP
  client restriction on wspr5. The configuration parses successfully and the
  Mac's `sntp time.local` query succeeds. GPS/PPS configuration was preserved.
- Completed both full loaded/armed/running waves after correcting the
  private preparation sequence. Independent original-data review verifies all
  192 accepted profile chunks, six BUSY applies and six confirmed cancels,
  twelve application PUT/409 refusals with unchanged readback bodies/ETags, and
  final observations of the same running job across the declared carriers.
  The waves took 244.665 and 228.721 seconds within the 300-second fixture allowance; each
  case stayed within 60 seconds and its shared pressure deadline. This closes
  the previously missing running-profile and final shared-state assertions.
  All six declared cases ended through owned ABORT/RELEASE. They do not claim
  six natural 45-second completions or RF qualification.
- Completed independent review of the full engineering resource capture:
  243 rows contain all 241 INFO samples over 7,200 seconds, with both directed
  waves. Heap allocation returned from 24,920 to 24,776 bytes, 144 bytes below
  baseline; peak allocation was 120,440 bytes. Every measured lwIP/BTstack pool
  returned to its own baseline. Minimum guarded stack margin was 22,128 bytes.
  Measured Bluetooth controller credits retained capacity eight and returned
  to eight free slots; actual send/completion counters advanced, with zero
  invalid samples or transport failures.
- Completed final authority and exit review. Four CRC-correlated TLS frames
  prove same-boot HELLO and empty STATUS with explicit null owner/job and
  inactive output, ending 1.249 seconds after the last resource sample. The
  immediate child INFO still had one closing network connection; its STOP
  remains intact. The later original parent INFO passes every strict quiet
  predicate 23.345673 target seconds later, with returned allocations, pools,
  preserved settings and zero flash erase/program activity. The private fixture
  now permits bounded asynchronous reclamation inside the existing cleanup
  reserve, retaining all guards, observations and deadlines. Three normal and
  three optimized controls, exact actual-data replay and independent source
  reassessment pass; no new target operation or repeated workload was needed.
  The exact owned worker, sockets and relay are retired, with clean relay
  cleanup and the board-lock holder retired. Working test state is retained.

## Validation and review

The affected native fixture was built and tested on wspr5 with firmware
disabled. Three selected CTests passed, including 15 Python fixture methods
and actual native two-peer/four-peer round trips. Those checks prove fixture
behavior and preservation, not live reset cryptographic refusal.

The maintained shared-authority suites passed 13 network tests and 54
composition tests in normal and optimized Python. The BLE suite passed 28
tests in both modes for the cache change, then 31 in both modes after the
deadline correction. The affected composition and setup suites were rerun
after that correction and passed 54 and 19 tests in both modes. The separate
fixture suite passed 32 tests. These are separate suite runs.

Independent source reviews examined the repairs together and found no
remaining actionable issue. A separate review covered the finite BLE relay,
the one-candidate cross-build workflow and exact source hashes. Firmware
compilation and target acceptance are recorded separately.

The following paragraphs retain the historical diagnostic sequence. Current
accepted scopes are stated above and in the closeout table below.

The automatic runner also exposed two preparation defects: a conflicting
parent timer and reused output filenames. The timer was corrected without
extending the workload's existing limits. A fresh output directory was
prepared for each campaign; prior output files remain intact. Stale output
collected after a filename collision is excluded from the new run's credit.

The fresh resource attempt stopped during its first profile upload. All 13
recorded application writes received successful replies, but the upload did
not finish within its existing 20-second preparation limit. No job was armed
or completed. Cleanup released ownership and returned the simulator to empty.
The trace exposed a client defect: its reply timer started after synchronous
fragment writes, allowing an exchange to overrun the caller's remaining
deadline. A bounded write-and-reply correction and controller-local execution
were source-tested and the controller-local health check passed; the resource
workload remained open at that checkpoint.

The first retained journal attempt authenticated the existing wspr4 peer, then
stopped at a redundant BLE time submission with an `uncertainty` reply. It
reached no profile open, write, apply or reset. Final INFO showed synchronized
SNTP time, 71 ms uncertainty and a 14-second sample age, with the simulator
empty, disabled and inactive. The continuation uses that actual SNTP readiness
for credential testing and removes the redundant first application reload.

That continuation completed the ordinary credential-B replacement and the
named stage-8 interruption checkpoint. After each restart, credential B
authenticated and credentials A and C were refused by TLS authority. The
selected profile remained generation 3 and retained the operational settings.
The next stage stopped during BLE connection establishment, before opening
or writing a profile. Final INFO showed healthy, synchronized, empty and
inactive B. The controller-local continuation also stopped at BLE Connect, with
`le-connection-abort-by-local`, before any GATT read or profile write. No new
journal assertion passed in that attempt. A subsequent 15-second capture proves B is advertising connectably with its
exact service. One controller-local health probe after that observation passes
Connect, authorization, HELLO and STATUS on the retained stage-9 boot. The
original connection failure remains unexplained. Stages 0 and 8 are not
scheduled for replay. The whole
journal and reset groups remained open at that checkpoint. The later
completed originals above close their declared automatic scopes.

A later journal continuation stopped in its isolated worker's Python loader:
`peer_client` was not available through the isolated import path. Its native
trace contains only client creation and the failed connect dispatch; backend
Connect, GATT and profile actions were not reached. The same B boot, profile
and unconsumed stage-9 fault remain available. The private loader correction now passes the actual isolated-launch
regression and independent review. The corrected worker refreshes discovery
before each Connect within the existing setup deadline; no case limit changed.

The first combined run from the current C state stopped after 54 seconds.
The private BLE worker retained its prior reply socket timeout while waiting
for the next command and exited during an ordinary idle gap. The original
worker traceback and both controller traces are retained. Cleanup completed
on the same B boot, empty, unowned and inactive. The correction concerns that
worker's idle wait; the workload and its case limits are unchanged. The next
attempt stopped before jobs because the original transfer correctly refused
three already-staged helper destinations. Reusing those exact bytes and staging
only fresh credential roles corrected that conflict. The following run reached
the first loaded-job case, then exhausted its 20-second preparatory profile
upload after nineteen acknowledged chunks. All stopped runs remain incomplete;
cleanup returned the same C boot to empty, unowned and inactive. A measured
finite upload preparation correction passed source review and retained the
unchanged job and acceptance deadlines. Its next run completed all 32 chunks
and the full 1,993-byte upload, then stopped at the final preparatory TLS STATUS.
The fixture had left that connection without traffic for 35.216 seconds; the
firmware closes connections after 30 seconds without progress. This establishes
a preparation mismatch, while the precise lower-layer close is inferred from
source and timing. No CLAIM, LOAD or job was reached. Cleanup preserved the
same quiet C boot and retired the owned lane. A bounded read-only verifier
refresh during upload passed independent source review. The next run completed
loaded and armed cases, which now pass independent original-data review:
four-carrier shared state, foreign refusals, application BUSY with unchanged
readbacks, and staged-profile BUSY/cancellation. Three CLAIM/LOAD attempts,
two ARMs and three terminal ABORT/RELEASE cleanups are retained; no flash
activity or boot/profile/access change occurred. It observed the
running state on all carriers, then stopped before running pressure because
19.885 seconds remained and its fixture required a full 21-second reservation.
No running-pressure or complete-wave credit is claimed. The successful loaded
and armed pressure sequences took about 9.240 and 10.354 seconds. The existing
acceptance requirements specify bounded completed assertions and an 18-second
pressure maximum, without requiring that full maximum to be available at entry.
The following correction removed that preparatory reservation and redundant INFO
reads while preserving the shared clipped deadline, all carrier checks and the
then-selected 30-second job, 60-second case and 240-second fixture wave limits.
That correction completed running station/hardware BUSY and unchanged readbacks,
which now pass independent review. The next profile step returned the exact
native `conflict` response: 30.116 seconds had passed since the last profile
progress, matching its production 30-second staging expiry. Final cancellation
against the retired proxy masked this as `peer_worker_retired`; the native
original preserves the first error. At that checkpoint, third apply and
cancellation remained unproved.
The succeeding scheduling correction performed profile BUSY/cancel before API pressure,
used a finite 45-second job within the existing 60-second ceiling, and a measured
300-second fixture wave inside the existing 600-second allowance. The 60-second
case, shared 18-second pressure maximum, per-call bounds, six-job workload and
7200-second/241-sample resource criteria remain unchanged. No firmware timeout
changes are needed; originals and clean cleanup remain retained.

The corrected run completed both reviewed waves and recorded all 241 INFO
samples over 7,200 seconds, followed by the raw final TLS authority exchanges.
It stopped in the immediate post-close quiet check: one network connection
was still active, while every other listed connection/buffer predicate was
clear. The later original parent INFO shows zero network connections and
returned TLS/heap allocations on the same quiet, synchronized C boot, with
unchanged profile/access/settings and zero flash writes. The original child
and parent STOP results remain retained. Independent resource and final-exit
assessment now accepts the complete raw resource/authority and later quiet
proof; no repeated workload was needed. The exact owned
BLE worker, sockets and relay have been retired after collection of the native
wire, with matching hashes and clean relay cleanup.

## Automatic closeout and remaining work

No declared automatic workstream remains open. Completed scopes are:

| Group | Accepted automatic result |
| --- | --- |
| B12J | Credential replacement, interruption/corruption cases and healthy-C recovery with selected trust and unrelated-state preservation. |
| R11P | Supported reset, retained-key cryptographic refusal, security-root rotation and exact unrelated-state/E10 preservation. |
| B12C | Engineering API/cold persistence, disconnect leases, inbound maximum BLE framing, both directed carrier/API waves, final quiet authority and owned-host cleanup. |
| B12R | Engineering two-hour resource return and measured pools/stacks/credits, plus consumer one-Save/twenty-STATUS overlap and durable cold preservation. |

The complete runner still reports STOPPED and `full_composition_qualified=false`;
these originals are not rewritten. Independent adjudication closes the declared
automatic work using the recorded two-hour capture, directed waves, raw final
authority, later strict quiet observation and exact lane-retirement proof.
Operator-dependent physical/fleet/interoperability/RF assertions remain open.

The private originals remain under the ignored execution directory. Selected
independent review bindings are:

| Review | SHA-256 |
| --- | --- |
| Two directed waves | `752372c5bc0a223be0b9738507e8419d771632c3d6c6c78c5c8318ca0209fd57` |
| Complete resource capture | `c6a69d08a8f459f7bd8dd430d08b3ff6c4901c45bf3462c1b52baa819f66e792` |
| Final authority and owned lane | `b95c55c3483b2e64fc7b34108afa08dca1182b8fe0b7ce43d8b60762c155de1a` |
| Quiet repair reassessment | `675dcaf5f1d92cef3abf6c1dda665aa0ce51de1c6eeb23f01ff55f487f9c7243` |
| Final B12C/B12R adjudication: zero remaining automatic workstreams | `599eba61d0d28b19d97643a549ffe5c3adcf779bcd105f89aa81071cd275abc3` |

The consumer AP failure has been narrowed: AP-only public HTTP worked, while
the post-station-return observer originally received no ARP reply. The new
firmware reports the AP interface up, link up and IPv4 `192.168.4.1` after
station return. A fresh check inside the actual claim window installed one
temporary neighbor entry and observed five outgoing SYNs with no reply. The
target's global TCP receive count rose by five and its send count by six;
those global counts do not identify the transmitting interface. The neighbor
entry and host connection were restored, with no Save, STATUS request,
firmware write or baseline restoration. This rules out the expired-AP
prerequisite seen in the earlier inconclusive attempt. One
observer reassociation attempt stopped before any HTTP request because its
preparation reserved 25 seconds of the remaining claim window and allowed
only 6.3 seconds for association. That stop does not establish a target
defect or satisfy Save/STATUS acceptance.

The ordinary Save continuation removed that redundant scan reservation and
refreshed the one observer association after actual station/SNTP readiness.
It retained the original 60-second claim and HTTP limits. All four actual HTTP
requests returned 200, including the single encrypted Save and durable public
readback. The target required no AP routing or lifecycle repair.

## Target and operator scope

B is serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`; A is serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`. Both are Pico 2 W / RP2350 and are
authorized by the operator for the connected SDR bench. Current automatic
composition uses the local inhibited standalone simulator at 138 MHz system
clock; it gains no RF timing qualification.

Working test states are retained between stages. There is no routine baseline
restoration. A checkpoint needed to compare retained keys or inspect a journal
is a test-specific transition, not a standard restoration loop. Credentials,
keys, flash backups, raw captures and generated firmware remain private and
outside tracked source.

Operator work stays last: the two available iOS clients, offline browser
visits, LED/GP14 observations on wired B, physical interruption and any
remaining physical/fleet/RF assertions. No additional phone inventory is
required by this continuation.

The user subsequently requested progress in the Phase 12 plan. Only its new
dated progress section and historical-section boundary heading belong to this
continuation; the plan's preexisting
changes, the other eight preexisting modified documentation files and the two
user backlog files remain outside this continuation's commits.
