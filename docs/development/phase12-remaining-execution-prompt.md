# Phase 12 completed operator acceptance continuation

Status: **CLOSED_SCOPED** (2026-10-06). The operator explicitly accepted the
final documented scope dispositions. Work on `devel` in
`/Users/lbussy/GitHub/WsprryPico` has completed the frozen fourteen-ID matrix;
**there is no remaining operator or device-action queue**. The
[current matrix](phase12-closure-matrix.md#final-accepted-scope-dispositions--2026-10-06)
and [final results](phase12-orchestratable-closeout-results.md#final-scoped-closeout-and-exit-2026-10-06)
record the earned assertions and exact exclusions. Earlier continuation
instructions below are retained policy/history, not authority for another trial.

## Final checkpoint

All four original automatic groups remain accepted: B12J credential journals,
R11P reset/old-peer refusal, B12C engineering carrier/API composition and B12R
resources/consumer Save overlap. C8/C10O commissioning on the selected phone/iPad
and A’s visible LED checks remain accepted. Offline Bluefy is unsupported and
excluded. No accepted soak, Save, LED, reset, journal or RF row was replayed.

The final four groups are closed by the results and explicit dispositions
below. Final RF totals are **19 acquisition attempts / 13 charged jobs**, at
an exhausted operator-approved 19/13 ceiling. Attempts 17 and 18 remain STOP;
the nineteenth original also remains FAILED_STOP_CAMPAIGN. The accepted longer
16.111-second hold and separate measured/functional components do not change
that strict original. **GP14 production default enablement remains deferred.**

A retains `6c7b14321003`, profile 5, inhibited/empty/inactive. B retains RF
`58afb2735c23`, boot `4345b097ce98a6889fcb42498c943386`, profile 3, epoch 4,
zero bonds, disabled/Aborted/inactive/safety-latched. Both are storage healthy,
GP14 released, clocks unsynchronized, and have zero BLE/network connections.
B is unowned at the retained same-boot functional proof with no later authority
mutation; the extra read-only exit HELLO reset remains STOP. The installed B
fleet assignment is paused, owned profiles/processes/connections are cleaned,
locks released, management and timing services preserved. Useful test images
remain installed; no routine exit reflash/restart/SNTP wait was added.

Read project instructions and the current matrix before any separately requested
future work. Preserve unrelated changes. Credentials, bonds, backups, captures,
generated firmware, screenshots and local SDK paths remain private and ignored.

<a id="operator-direction-20261005"></a>

## Operator direction — 2026-10-05

Keep useful test firmware/configuration installed between tranches and at exit.
The operator authorizes A and B, including transmission on the reported connected
SDR rigs, and trusts the local wspr hosts and Mac. This supersedes the earlier
B-only/wspr4-excluded scope and blanket inhibited-image/restoration instructions.
Default production firmware behavior and intended-test limits remain unchanged.

Use the available phone, iPad and laptop. The operator now has GP14 buttons
on both A and B; no wire transfer is needed.
Do not request another phone inventory or unnecessary purchases. Complete source-bound
preparation, protocol collection and analysis automatically, and gather
necessary physical actions into one practical operator session.
That session is complete; this recorded policy does not reopen it.

- B: Pico 2 W / RP2350, USB serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`.
- A: Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`.

The earlier automatic closeout retained B on engineering source
`c0d2bd53e4bd`, profile generation
2 and operational generation 5, and A on consumer diagnostic source
`133ca93cc2a1`, durable profile generation 3. These are recorded exit states,
not substitutes for checking identity and applicable source before a new case.
Use one controller per device, with its exclusion/action locks. Read-only
reviewers must not manipulate the same device or fixture concurrently.

No routine baseline reflash, full-flash comparison, reboot, SNTP wait or
AP-absence campaign is required. Reuse compatible private backups; acquire a
new one only when changed state or a destructive assertion requires it. Restore
only for actual device recovery or a named assertion. Cold readbacks, restarts,
E10/settings comparisons, AP withdrawal and cutoff evidence remain part of
cases that require them. Never repeat an uncertain destructive request simply
because its reply was lost.

## Completed frozen four-group session

1. **B12L checked LED error and GP14 overlap:** one checked-driver error/retry
   fixture boot and one named repaired normal exit pass. Direct visual checks
   stay accepted. Exact GP14/erase-program coincidence is unmeasured and
   explicitly excluded; the narrower two-second flash-safe pause is retained.
   Complete physical LED-failure detection is not claimed.
2. **R11P/B12J physical interruption:** one completed-header/precommit USB power
   cut passes exact old-profile/bond/security-root/settings/E10 selection. The
   second actual cut’s timed reset-intent assertion remains STOP and is now
   explicitly excluded; later clearing/recovery passes. In-pulse power loss is
   also excluded. Two actual cuts occurred; one is qualified, with no retry.
3. **B12C actual peers and interoperability:** actual native-Pi peer and one
   installed fleet member/application simulator job pass. Three actual bonds
   do not qualify the four-bond/fifth-peer boundary. That boundary, iPad
   engineering BLE, wspr5 post-release connection and simultaneous/full
   eight-member fleet are explicitly excluded; compiled/advertised limits and
   one JobService/ownership authority are unchanged.
4. **G7 long RF hold to portal/F12 exit:** the nineteenth attempt retains one
   independent 40.020-second capture, 1.261 ms nominal/54.828 ms conservative
   cutoff, no reactivation, AP association at 8.661 seconds and later same-boot
   usable setup/latch refusal. The operator accepted the measured 16.111-second
   hold and final scoped closure. Strict 50 ms cutoff and HTTP/operator
   confirmation within 90 seconds remain unqualified; original STOP is retained.
   Five earlier strict rows stay accepted. Default enablement is deferred;
   no automatic retry, new RF job or additional physical action follows.

The Phase 13 feature backlog and Phase 14 final qualification remain separate.
The selected closeout does not qualify broad RF performance, reliability or
full fleet interoperability.

## Exit, review and publication

End test jobs, prevent unintended schedule launches, and record brief current
identity/image/owner/output/schedule/health state. Retain useful firmware and
configuration. Close test connections, remove only owned temporary fixtures and
processes, and release the selected device's locks. Obtain additional flash,
restart, SNTP or AP observations only for a named assertion or recovery.

Use the established Linux workflow for C++ and retained pinned firmware tools.
Do not repair the Mac compiler, install dependencies or download an SDK as an
incidental step. Documentation-only changes need link, evidence/consistency
and whitespace review, rather than unchanged C++ or target tests.

Review actual changes, exercised behavior, original evidence and acceptance
claims. Repair actionable findings, rerun affected checks and reassess. Update
the matrix and existing result records with only earned scope; preserve failed
originals. Commit/push when requested, independently verify remote parity, and
report completed assertions, approved exclusions and actual repository/device
state. Phase 12 is closed within the scope explicitly accepted by the operator.

## Historical automatic checkpoint

The earlier prompt began at `10d66719c775209f328d66fdc08603f1e2ed6a56`, following
`f2dd23d0d95dd8dc846e241ce072195ac19db3df`. Its four remaining automatic groups
were completed by the later closeout. The
[historical execution review](phase12-remaining-execution-review.md) retains
that checkpoint's diagnostics and acceptance. The original full automatic
instructions are retained in Git history at `dd419af`; they are not current
work. The roadmap and LED/Si5351 documentation previously excluded from the
automatic commits are now included in this requested documentation review.
