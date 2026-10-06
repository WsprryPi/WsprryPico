# Phase 12 remaining acceptance execution review

Status: **HISTORICAL EXECUTED CHECKPOINT / OPEN_PARTIAL**. The subsequent
[automatic closeout](phase12-orchestratable-closeout-results.md) completes the
four workstreams left by this record. Zero declared automatic groups remain;
operator-dependent and broader qualification work stays open in the
[current matrix](phase12-closure-matrix.md). The failures, restoration evidence
and acceptance below retain their original checkpoint scope.

This record executed the then-current
[remaining acceptance prompt](phase12-remaining-execution-prompt.md), retained
in Git at `dd419af`, on `devel`
from `10d66719c775209f328d66fdc08603f1e2ed6a56`. Six automatic workstreams were
open at the starting checkpoint; four remained after the complete narrow
C8T/R11F readiness and R11A automatic assessments below. The earlier automatic B12T/T5
acceptance is retained. The fourteen existing closure-matrix IDs and physical
gates are unchanged.

## Actual prerequisite diagnosis

Independent comparison found exact checkpoint/profile/AP SSID and password
agreement in the preceding failed receiver run. Its first failed join preceded
AP readiness; its final five observations were JOIN after the production
30-second failure hold and one-second leave interval. The unchanged 30-second
diagnostic ended while that later join was pending. No credential, country,
channel or authentication defect was demonstrated.

One fresh reviewed diagnostic changes only startup ordering: activate the
owned wlan0 AP and verify its fresh exact beacon with idle wlan2 before the
single checkpoint boot. The two phases share the original 160-second remote
deadline; NM, scan, station and proof limits remain 30 seconds each, with the
original 340-second body and 900-second parent limits. No timer was extended.

Campaign `ap-before-boot-live-d4fd6b04312b4141b04aa81560915914` completed in
174.857 seconds with one AP activation, connected station proof and two
original USB authority bookends. It issued zero SAVE, SUBMIT, simulator or RF
jobs. Its result is explicitly `DIAGNOSTIC_COMPLETE_NO_ACCEPTANCE`; this
establishes a usable setup for that run, not a universal failure cause or a
completed carrier/recovery acceptance group. Original failed runs remain.
Final byte restoration matches the original full 4 MiB image; independent
result and restoration reviews pass. The first fresh F12 exit stopped on an
original `iw` return code 240 with empty stdout and the exact device/resource
busy error, before any complete scan. Its incomplete result remains retained.
A separately reviewed observer handles only that observed response with finite
polling inside the unchanged 15-second total scan deadline. It retains every
attempt and uses only the successful call's freshness bracket. Its new exit
passes independent original-result review: six same-boot INFOs, two explicit
CRC-correlated null-owner/job exchanges, two complete fresh AP-absence scans,
unchanged management and both released locks. Both new scans succeeded on
their first call; live busy recovery was not exercised by this successful run.

## Narrow reset-recovery fixture

The retained BLE old-peer test unnecessarily depends on Pi hotspot setup.
The target already resumes a durable provisioning-reset intent before starting
transports. A named host-only `--prepare-reset-intent yes` fixture now creates
that intent through production `ResetCoordinator::begin` from a healthy exact-B
runtime profile with one bond and disabled operational state. It verifies all
other access fields and every byte outside the access journal remain exact.
The target, rather than the host fixture, performs reset recovery and secret/
bond replacement. This does not add a USB or GATT reset command.

One native cold-resume round trip exercises production reset storage, epoch,
profile/bond clearing and operational/E10 preservation; a separate CLI check
refuses an input without the required real one-bond checkpoint. These are host
checks. Live pre-reset encrypted peer matching and post-reset cryptographic
refusal remain required before accepting the R11P automatic assertion.

The fresh B-only campaign first proves the retained Pi peer can authenticate
to the exact generation-2 checkpoint without Pair. It seeds one durable intent
only after that proof, and target recovery clears the bond and rotates both
local roots. Its single old-peer attempt returns BlueZ
`org.bluez.Error.Failed / le-connection-abort-by-local`; this is inconclusive
and supplies no cryptographic-refusal acceptance. The subsequent inspection
stops on an eight-second SSH transaction timeout with empty original streams,
not a demonstrated native-parser refusal. The original full flash is restored
exactly and independently verified; the fresh F12 exit also passes independent
original-result and released-lock review.
No uncertain destructive operation is repeated, and R11P stays automatic work.

Fresh private packet `12abad3071984a71bce0aee66f772b73` adds complete read-only
USB BLE STATUS bookends around the single old-peer Connect, with same-boot
INFO/source/generation guards inside the existing 20-second limit. The
authenticated retained-peer prerequisite still precedes any reset; no Pair,
enrollment or cache change is added. Nine checks pass normally and with
optimization; independent source review `692b28ec` is clear. It has not run.
The later journal common setup removed the Pi's retained B bond and its Pair
failed. Target full-flash restoration does not restore that deleted host key,
and no matching host-bond backup/restore hook is retained. The current
authenticated old-peer prerequisite is therefore not demonstrated; this
packet must not run merely to obtain counters. Target connection counts or a
disconnect reason alone cannot supply cryptographic-refusal acceptance or
establish the earlier lower cause.

## Accepted station-readiness subset

The separately bounded station-generation-7 case completes in 301.548 seconds
including restoration. The owned canonical AP and fresh beacon precede the
single checkpoint boot, with its SNTP responder disabled. Original INFO and
public HTTP observations establish offline readiness pending; one responder
enable then supplies accepted trustworthy time, five synchronized ready
observations and a ready public response. There are zero SAVE, SUBMIT or jobs.

Independent review verifies the entire reserved region after readiness equals
the accepted generation-7 station checkpoint, including both clients, TLS,
access, operational configuration/cursor and E10. Its exact standard restoration
and fresh F12 observer pass separately. This accepts the station warming subset
of C8T/R11F. The later network warming and absent-TLS results are recorded below. No engineering mTLS
admission, RF or physical assertion follows from this case.

## Native transport repair

The first network-generation-8 attempt stopped in its native checkpoint
preflight before acquiring B, loading a checkpoint or creating a host fixture.
Its original eight-second SSH failure remains retained. A retained-file check
then showed a complete framed native reply with SSH compression enabled; the
uncompressed comparison had stopped before a validated reply. The lower-level
timeout cause is not established. Independent review verifies the bridge
change adds only `ssh -C` and preserves host, native tools, framing and case
limits. Fresh cases use the reviewed bridge; no further SSH-only timing work
is needed. SSH speed supplies no Phase 12 acceptance.

The fresh compressed network case passes checkpoint inspection and loads the
accepted generation-8 image after owned-AP readiness. It stops during the
110-second observer association: fifteen complete scans do not contain the
exact B SoftAP, alongside three partial scan timeouts and five busy responses.
The final full scan times out with 15.966 seconds remaining. No case INFO,
public readiness response, time enable or post-case native preservation check
is reached. Its 313.039-second stopped result, original scans and failed
transcript remain retained. Exact restoration and the new F12 exit both pass
independent review. This attempt supplies no network acceptance; the later
distinct continuation below is assessed separately.

## Network readiness and pending-TLS continuation

A distinct owned-loss continuation, campaign
`consumer-readiness-network-owned-loss-live-153976bf1a5c497f9d340bded1eea04e`,
completes in 358.288 seconds including restoration. Its exact owned AP is
ready before checkpoint boot. One controlled down/up cycle holds the owned AP
down for 60.133 seconds; the original shared observation spans 188.859 seconds inside
its 300-second limit. Offline and ready public GETs, one time enable, two
original correlated saved-peer SNTP replies and five same-boot ready samples
support the narrow generation-8 cold network-readiness acceptance. There are
zero SAVE, SUBMIT or jobs.

Independent native/readback review verifies the selected profile and entire
reserved region equal the accepted checkpoint, with both existing clients and
trust bytes preserved. Exact standard/full-flash/E10 restoration, fresh F12
originals and both released locks pass separately. This accepts the network
warming subset of C8T/R11F; it does not complete R11A, prove a new engineering
TLS client admission or erase the earlier stopped network attempts.

Campaign `consumer-readiness-pending-tls-owned-loss-live-13ab78f1728240d3bbcb2174f4307897`
is **STOPPED** at the unchanged 340-second parent-body deadline. Its child
records generation 8 to 9 and readiness/materialization observations, but
`after-readiness.bin` and the native/TLS readiness assessment are absent.
Those observations do not accept the whole pending-TLS assertion. The
432.830-second result includes restoration; exact original full flash and E10
restoration pass independent review. Its fresh F12 exit and released locks pass independent original-result review.
No case timer is extended and no save is replayed.

The reviewed pending-only ordering repair now collects the mandatory cold
snapshot and native/TLS assessment before archival collection. It is applied
to maintained source; 33 checks pass normally and with optimization, and
independent review `ad706d8e` is clear. Fresh campaign
`consumer-readiness-pending-proof-order-live-017ab271113c41e7ac0a2fdeea2a1021`
completes in 393.026 seconds including restoration. Its controlled owned-AP
loss holds for 60.131 seconds; the shared observation spans 234.406 seconds
inside its original 300-second limit. Two correlated time replies and five
same-fresh-boot ready INFOs accompany one autonomous generation-8-to-9 TLS
materialization. Mandatory cold readback and native/TLS assessment now pass,
with protected regions, operational configuration/cursor and E10 preserved.
There are zero SAVE, SUBMIT or jobs. Independent outcome `4e868ac0`, exact
full restoration and fresh F12/lock review `07cd1890` pass.

This seed deliberately contains zero clients. The ready public endpoint stays
false, with three unavailable observations; this accepts only the pending-TLS
materialization assertion and supplies no engineering client admission. The
station-generation-7 and network-generation-8 cases separately preserve their
existing two clients and trust. Together these complete the automatic C8T/R11F
readiness work, while the original pending timeout remains retained.

## Engineering discovery and consumer overlap

The first R11A engineering campaign stops at `discover_ble` before provisioning
or the network-recovery body. All 73 original snapshots within the existing
15-second scan have zero expected-name matches. The separately verified B
address is present as a service candidate with a Name that does not match;
the actual Name and fresh air advertisement were not retained. This establishes
the failed host selector prerequisite, not a production naming or Bluetooth
cause. Its exact restoration passes independent review; this run supplies no
R11A acceptance.

The independently reviewed discovery repair is now applied to maintained
scripts. Optional explicit selection admits only the already verified public
B address and expected service, rejects ambiguity and retains the actual
cached Name without claiming a fresh advertisement. Actual fresh USB INFO
bookends bind B's source, boot and generation around discovery. Connection
then requires the actual GATT device ID and typed generation, followed by
another same-boot USB guard before provisioning field writes. The legacy
name selector remains the default, and the original 15-second discovery and
case limits remain unchanged. Four fresh source-bound engineering packets
are prepared; their source checks supply no carrier or job acceptance.

Fresh campaign `network-bound-B-live-9e978df047e349e6ada17510054c223e`
completes the narrow loss/fallback/reconnect subset in 146.450 seconds. The
profile apply is acknowledged after the actual GATT identity guard. Forty-one
original INFO/CRC STATUS pairs, fallback portal proof 71.873 seconds after
observed loss and 30.229 seconds of recovered synchronized stability support
independent subset review `6c697ba6`. There are zero simulator/RF jobs and no
cleanup errors. Exact full-flash restoration passes review `619789e1`; the
fresh F12 assessment remains separate. This run did not stimulate manual lease
or deliberately pending-reply retention. The already accepted inhibited B
`6105f9d` manual-policy result is retained: 1,520.711 seconds of physical hold
and a conservatively bracketed 597.356938–603.586852-second released lease.
The coordinator, constants, button runtime/control and manual callback wiring
are byte-identical at `c0d2bd5`; scoped reuse review `4bf5d59a` is clear.
The original monitoring gap and lack of independent beacon-off measurement
remain recorded. Current engineering/restore images have GP14 disabled, so
reuse does not qualify their physical trigger or default enablement;
`ACCESS SOFTAP` grants a separate 120-second grace. At that point deliberately
pending-reply retention remained automatic for R11A; its accepted result is
recorded below. Other unaccepted assertions remain in their existing
workstreams.

The pending-reply campaign
`pending-reply-retention-live-d7f506f4eebd41268b2b8d576a85e9f1` stops on a
TLS receive timeout after one public-asset GET intent. Neither complete
headers nor partial receive bytes were retained on that failure; no pending
output across grace expiry, complete drain or withdrawal acceptance exists.
Independent stop review `ebd8027d` preserves that boundary and the unknown
lower network/server cause. A distinct source-cleared discriminator
(`65a85d3a`, eight checks normally and with optimization) first requires a
complete ordinary-window GET of the same asset before one clamped GET during
the same single `ACCESS SOFTAP` 120-second grace. It retains partial streams
and matching INFO, and replaces the individual two-second receive cutoff with
the remaining original absolute response/grace limit. The 15-second production
connection cap and original case/controller limits remain. Preparation and
actual-config review supply no pending-reply acceptance; the old failure is
unchanged.

That distinct discriminator actually runs as
`pending-reply-retention-live-3c099cbdb34f4eb2945b50cb994ed811`. The ordinary
GET completes HTTP 200 with the source-verified 27,188-byte asset digest in
0.805 seconds. The clamped connection completes TLS and sendall but returns
zero header bytes before its original ACK-plus-120-second cutoff. INFO with
the failed stream still open then records one active connection and 5,840
outbound pending bytes. The counter accounts for TLS control as well as data;
this supports only joint observation of a connection and pending output, not
queue-only causation or complete retention acceptance. Required post-grace
CRC/beacon, full same-connection drain and
withdrawal proof are not reached. Independent stop `fff978d0` and exact
restoration `c9f2b690` preserve this outcome. The first F12 exit stops at its
15-second first-scan timeout (`3e98eda8`); a separate complete fresh F12 exit
passes `0eafc325`. The original incomplete observer remains retained.

Source-cleared packet `f99b7307ce7c4f94b2839d51c1a73901` moves the clamped
header/prefix read after the existing post-grace INFO, CRC and fresh B beacon
checks. The same connection must still deliver HTTP 200 and the complete
exact asset digest before its original preconnect-plus-14-second end. The
ordinary GET remains mandatory, with two total GETs, one ACCESS 120-second
grace and unchanged 15-second server, 400-second remote, 600-second body and
900-second controller caps. Ten checks pass normally and with optimization;
independent source review is clear. Its actual campaign
`pending-reply-retention-live-6c8d5ffaac7b4db398f8a86f65811314` stops during
preboot AP preparation: one NM activation succeeds, then the first full wlan2
beacon scan returns 240 in 0.008416 seconds, with empty stdout and the exact
46-byte device/resource busy error. No checkpoint deployment, console, CRC,
ACCESS or GET occurs. Independent stop `2c9f78f9`, exact full restoration
`49042dfb` and fresh F12 review `273f15da` preserve that boundary.

A fresh packet reuses only the already reviewed exact-EBUSY handling inside
the original 15-second total scan deadline, with at most 31 attempts and
0.5-second pauses. Every original is retained; a complete legal fresh positive
beacon remains required. Thirteen checks pass normally and with optimization,
and independent source review `c21152a0` is clear. Its actual campaign
`pending-reply-retention-live-23b1b9323c0f49358a9904283d60bcf9` reaches the
post-grace joint INFO, CRC and fresh B beacon checks: one active connection
and 5,840 outbound pending bytes are observed 120.389 seconds after ACCESS
acknowledgement. The ordinary GET has completed the exact asset. The same
clamped connection then supplies complete HTTP 200 headers, but its first
64-byte body-prefix read times out. The header read takes 7.053 seconds and
leaves 2.560 seconds before the unchanged preconnect-plus-14-second end.
No body prefix, complete digest, drain/close or withdrawal acceptance exists.
Independent stop review `adcccfab` preserves that partial joint observation.
The 446.968-second stopped result includes exact full-flash restoration,
independently reviewed as `41e51a87`; its separate fresh F12 review passes as
`a3a2a5ef`. The receive-window clamp remains active during drain, so the proposed
narrow fixture correction releases it only after the existing post-grace
checks while retaining the same connection, full response proof and original
deadlines. Fresh inert packet `a4163e4709254ea1b9b6db7ef9c10ef3` implements
that correction; fourteen checks pass normally and with optimization, and
independent source review `b68f74fb` is clear. Source and configuration
admission do not establish a target/server cause or add acceptance.

Its actual `pending-reply-retention-live-664d7120ed274dd6a3095c05a7bc4d8a`
case **STOPPED** in 424.855 seconds at the final observer link-withdrawal
guard. The ordinary exact asset completes; after the existing post-grace
INFO, CRC and fresh B beacon proof, the same connection's receive window is
released. It then delivers HTTP 200 and the complete exact 27,188-byte digest
and closes 4.508 seconds after preconnect, inside the original 14/15-second
bounds. Subsequent INFO reports zero active connections and pending bytes,
and the fresh B beacon observation is absent. The single `iw link` query
1.120 seconds after close still reports B's association, so complete case
success is refused. The existing 30-second withdrawal window still has
28.868 seconds remaining; source performs only this immediate link check.
No lower radio cause or future client-cache teardown is inferred. Independent
original review `120bf05d` accepts the canonical bounded pending-reply
criterion: joint active AP connection and outbound pending-output retention
past the grace, complete same-connection response delivery/close and fresh
actual AP withdrawal. The field contract requires bounded AP absence, rather
than immediate client link-cache teardown. The parent **STOPPED** result and
extra failed assertion remain preserved; no retry or timer change is needed
for this accepted criterion. Exact full-baseline restoration passes
`ad25d11c`, and separate fresh F12 review passes `fe297a58`. Combined with the
retained loss/reconnect and scoped historical manual-policy results, this
completes R11A automatic work. It does not prove queue-only causation,
universal withdrawal behavior or current-image physical GP14 operation.

The original consumer Save/STATUS packet stops before any host/Pico action:
its controller's host-capture fixture hash does not match its actual frozen
runtime fixture. A fresh `4e4437086c604a5195fd3fb84190dbee` packet derives that
binding from the exact runtime and preserves the reviewed host-capture helper,
case bodies and all prior originals. Ten checks pass normally and with
optimization, including actual authorized controller admission reaching exactly
one denied host-capture call. Independent reassessment is clear. The fresh
`consumer-save-status-live-0451c532ffed4a45bb758da4cd532b5c` campaign then
**STOPPED** before the Save/STATUS dispatcher: the guard was reached 448 seconds
after campaign start under its 600-second whole-body clock, leaving insufficient time for
the unchanged 390-second dispatcher/reboot/readback reserve. The guard did not
issue a save. Forty-three fallback INFOs retain generation 6 and zero flash
erase/program attempts; no Save/STATUS dispatcher result or job acceptance
exists. The separately collected final full-flash readback equals the original
4 MiB baseline exactly. Independent restoration review `b57b3056` and fresh
F12 original-result/lock review `3a31763d` pass.
The case's limits remain one save, at most twenty STATUS requests per available
authorized carrier and ten minutes, with actual B SoftAP admission required.
The reviewed clock-placement correction starts the 600-second case once at
retained warm-ready INFO and omits only the redundant restore of the same
already verified baseline. Its first execution,
`consumer-save-status-live-e380a7b7c61a4aa7b0b96e317a1174ad`, also **STOPPED**
before the dispatcher and Save: the absolute 900-second controller could not
fit the unchanged 390-second case plus 90-second restoration admission
reserve. Original monotonic fields show 427.889 seconds from controller start
to warm readiness, leaving only 472.111 seconds even before the observed
60.590-second station loss. No Save/STATUS acceptance or jobs exist. The
collected full 4 MiB readback again equals baseline `607bf46b`; independent
restoration review `60be4ac9` passes. Fresh F12 remains a separate exit gate.

The next inert packet explicitly increases the private overall preparation and
case controller from **900 to 1200 seconds**. The actual case remains at most
600 seconds from that same one-time warm-ready boundary, with dispatch 240,
alarm 280, measurement 120, one Save and at most twenty STATUS requests per
available authorized carrier. The 390-second case and 90-second restoration
admission reserves remain unchanged; the latter is planning, not a timing
guarantee. At the observed warm-readiness duration, 1200 leaves 772.111 seconds,
or 652.111 after the full existing 120-second fallback allowance, above the
480-second admission requirement. Slower future preparation must still stop
before Save if the reserves cannot fit. Thirteen checks pass normally and
with optimization, including actual controller admission with endpoints
denied; independent source review `8d29b0e3` is clear.

That 1200-second packet,
`consumer-save-status-live-7a2d33c06b2442c4ba8d300e86f39c8f`, reached the
dispatch boundary but **STOPPED** before remote dispatcher execution: two
erroneous positional helper names made `RemoteAdapters.invoke` receive
multiple values for `timeout`. No Save or STATUS measurement was issued.
Exact baseline restoration passes independent review `ab3b4a59`, with no
cleanup errors; fresh F12 passes separately as `8d243305`. A fresh inert
repair removes only those two arguments. Its actual-call AST regression
reproduces the original TypeError against the real method signature and
admits exactly one dispatcher/dictionary call after the correction.
Fourteen checks pass normally and with optimization; independent source
review `a58b5f4e` is clear. All case limits and prior originals remain unchanged.
No consumer Save/STATUS acceptance is claimed.

Fresh `consumer-save-status-live-75a2728373f44d54826177960543e4c1` also
**STOPPED** before deployment or AP activation. Its native populate reply
reports return code 0, `OFFLINE_FIXTURE_READY` and a 4 MiB output, but only
621,542 binary bytes arrive before the original 8.0359-second SSH timeout.
The full output digest cannot be validated and no output is published. Zero
Save, measured STATUS or jobs occur. Independent stop `d73c9392` and exact
baseline restoration `ecc40d2b` are retained; fresh F12 independently passes
as `5d3d7dda`. The source-cleared private transport
correction gives only `populate` a 60-second SSH and 65-second outer setup
allowance; other operations retain 8/10 seconds and the native body retains
six seconds. Eighteen checks pass normally and with optimization, including
the unchanged fourteen consumer controls and four transfer controls;
independent source review `49bb2389` is clear. Source work supplies no case
acceptance or lower network cause. The actual one-Save/STATUS measurement
limits are unchanged.

The transfer-only packet then runs as
`consumer-save-status-live-c7d9a233c8e549b6920125ec699eee14`. Native populate,
full output publication and parent warm readiness pass. The case **STOPPED**
before Save at its first baseline STATUS attempt: after the owned AP returns,
the five-second baseline carrier path polls INFO while station link is `-2`
and Plain LAN WTP readiness is false. One STATUS attempt is charged, but zero
STATUS requests are transmitted; Save, simulator/RF jobs and erase/program
attempts are all zero. The missing premeasurement readiness barrier is a
concrete harness prerequisite; the lower station reacquisition cause remains
unknown. Independent stop `3f78b906`, exact full restoration `a678940c` and
separate fresh F12 `e749050d` pass.

A narrow bounded gate is prepared before baseline measurement, using
the original 240-second dispatcher end while reserving its existing
120-second measurement window. Poll spacing is at least one second and each
STATUS call retains its original five-second cap. The one-Save/twenty-STATUS
counts, case bounds and mandatory actual overlap proof are unchanged. This
fresh `e6567ffae3664ce0a039475ba76eb3bf` packet passes twenty checks normally
and with optimization, including actual staged child admission;
independent source review `6f08c900` is clear. Preparation supplies no
consumer overlap acceptance.

Its actual `consumer-save-status-live-674f4fd49d954a5a8cf726fb8df09f63`
case **STOPPED** after the readiness gate at measurement's first public GET:
TCP connect to B's portal times out before a request is transmitted. The
three-observation readiness gate passed and an earlier public GET completed,
but ACTIVITYTRACE, STATUS requests, encrypted claim/Save and concurrent
measurement never begin. Independent stop `9718ef33` confirms zero Save and
job attempts. No station, server or radio cause is established by the timeout;
there is no fresh beacon/link sample at that failed connect. Exact full
restoration independently passes `7e3c3c8e`; separate fresh F12 passes
`fc14ef5c`. No consumer overlap acceptance is added.

Fresh carrier-rejoin packet `6c6ecc1963b34de894ba25f7af32c970` reached
preassociation in `consumer-save-status-live-83cc5ad5376a489cbfd1e7bb3690a3b3`
then **STOPPED** at legal-frequency parsing. The successful complete `iw phy2
info` original renders integral values such as `2412.0`; the integer-only
parser returns no legal frequencies. Independent original replay `a75f4d3c`
reproduces this concrete harness defect. Station return, observer activation,
GET, STATUS, Save and jobs have zero attempts. Existing full readback equals
baseline `607bf46b`; independent restoration `c08523aa` passes. Root's fresh
F12 observer and released-lock checks pass; independent exit review
`a44c3b3c` passes separately. The used packet and originals remain preserved.

The integral-frequency derivative `012170d25ecd4de396884a5bcd62d476`
completed in `consumer-save-status-live-b0d3f112d228465da39fa99f863b5407`
with **STOPPED**, without consumer acceptance. Its 65 wire records include one
owned station return, an earlier public GET200 and ten readiness polls. A fresh
legal B beacon and matching wlan2 link at 2422 MHz pass immediately before
measurement; no rejoin is needed. Measurement's first TCP80 connect times out
in 5.009 seconds before request transmission, STATUS, Save or jobs. The parser
repair and carrier discriminator pass, but target AP netif, DHCP, DNS and
listener state are unobserved; the lower cause remains unknown. No further
consumer replay is justified without a demonstrated repair. Exact full
restoration passes `844f0251`, and separate fresh F12 passes `379c3c19`.

## Checkpoint-start application preparation

Private packet `application-checkpoint-start-preparation-d5f3baf5c24c4021a8691b7c595920bc`
is source-ready for the independent B12C API slice. It uses retained source1,
generation2 checkpoint A and its TLS clients, with an owned AP and fresh beacon
established before one checkpoint boot. It invokes the real application
route for four station/hardware saves, pending CLAIM inhibition, one normal
REBOOT and cold TLS/WTP/readback proof, without RESET, discovery, ENROLL,
Pair or jobs. Original warm180/idle60/cold180, dispatch450 and controller2400
bounds remain. Seven checks pass normally and with optimization; independent
source review `0658a18f` is clear. Actual host capture `f655` and configuration
`4585` finalize only authority and the two host-before fields.

Its actual `application-checkpoint-live-14182cb7cc114e81a1b167901773d0b9`
run **STOPPED** after 185.374 seconds. The exact fresh owned AP preceded one
checkpoint boot and accepted-time warming. Initial authenticated WTP
HELLO/CAPS/STATUS replies prove null owner/job; authenticated TLSv1.3 with
`http/1.1` then opened and one first GET `/api/v1/application` was transmitted.
Receive timed out under the original three-second exchange end before any
API Save or normal REBOOT. Eighteen private wire rows retain no HTTP RX
record; response extent and context/TCP/TLS/reply timing split remain unknown.
Independent HTTP source/original review `4e0311bb` identifies the client's
EOF-before-Content-Length dependency and loss of accumulated reply bytes on
exception, without assigning a target cause. Exact full607/E10 restoration
and 7,097 standard-image pages pass compatible review `9a432296`; the prior
`d62cbc72` retained-byte review remains unchanged. Cleanup is the parent's
empty error report; separate fresh F12 independently passes `47694335`, bound
to the compatible restoration receipt. No API or full-composition acceptance
is added.

A fresh private HTTP derivative `d02d017e99fc4f90907296f880d18570` changes only
`resource_http`: exact canonical framed-body completion needs no EOF, and
bounded partial originals/phase timings survive exceptions. The same three-
second absolute end and all request/save/reboot/case bounds remain. Thirteen
checks pass normally and with optimization; two old-behavior controls fail
with the original function. Independent source review `eea29fd8` is clear.
Root finalized actual configuration `6a56` and host-before `b33`, and its
`application-http-frame-live-de894dd7e9cc4e7c89d70d490abaab29` run **STOPPED**
after 186.319 seconds. Framing succeeds: the complete 476-byte HTTP403
`invalid_host` response finishes in 1.458 seconds inside the original three-
second end. Twenty-one wire records preserve the request and complete reply;
Host and Origin both contain explicit default port `:443`. Independent
source/original review `363787bb` proves a helper authority defect: the exact
c0d canonical authority rejects explicit port 443, and the server omits that default
port. API Saves, test REBOOT and jobs remain zero. Compatible full607/E10 and
7,097-page restoration passes `133866f5`; parent cleanup is an empty error
report. Separate fresh F12 independently passes `1c72a17c`, bound to that
restoration receipt. The earlier 14e reply extent remains unknown;
this 403 result adds no retrospective response or API acceptance.

Fresh private authority derivative `11d1c8b72e2e4597957e5382180b1730` changes
only that expression, omitting port 443 while retaining nondefault ports. Fourteen
checks pass normally and with optimization, and the former expression fails
the real transmitted Host/Origin test. Independent source review `980e7030`
is clear. Actual configuration `7eea5eb5` and host-before `2086f46e` now bind
the fresh case; independent actual admission `7b0cbf55` is clear. The same
reviewed function is now in the maintained composition helper. Independent
maintained review `1ea318c8` confirms 53 normal and 53 optimized full-suite
checks pass; only the helper function and HTTP test class change. Current
fifteen-path integration review `c185d85b` is clear. Planned publication covers
those source/test paths and four owned documents; these source checks supply
no live acceptance.

Its actual `application-authority-live-b1ff136bdcba4f349deaf052daf9246e`
run **STOPPED** after 242.768 seconds. Independent subset review `d0dfca86`
accepts only the idle API slice: four exact save/readbacks advance generations
2→6, with unrelated settings preserved, four target/revision negatives,
pending restart, two CRC-correlated CLAIM BUSY refusals and fifteen null-owner/
job STATUS replies. The normal test REBOOT is acknowledged once and produces
a fresh cold boot. Cold application proof then stops during TLS handshake
under the same three-second exchange end, before its first cold GET. Twenty existing INFO originals are retained:
six warm and fourteen cold, collected as `343870c7` with zero new device reads.
The fresh cold boot is synchronized with accepted time and reports its control
listener configured and listening. Its `lan_wtp_ready=false` is expected for
the engineering-TLS mode; no missing-listener cause is established. Parent
cleanup reports no errors. Exact full607/E10 restoration independently passes
`45782054`, and separate fresh F12 passes `7797b2e5`: six synchronized quiet
same-boot INFOs, CRC null-owner/job bookends, two complete legal fresh scans,
unchanged management/radios and both released locks. Cold API saved/active
pins and revisions, and cold TLS/WTP shared admission, remain unproved. No
full B12C or composition closure is claimed, and no retry or source change is
proposed. All used packets and
stopped originals are preserved.

## Journal common setup stop

Campaign `journal-bound-B-live-eeaa4eaa91a14137917e14fbfab4497c` stops in
common setup: one supported ENROLL precedes one Pair, which returns the
original BlueZ `ConnectionAttemptFailed: Page Timeout`. GATT identity and
profile START/LOAD/APPLY are not reached; zero journal cases and zero jobs
start. Independent stop review `5f618f7a` records the helper's acknowledged
enrollment check while retaining the absence of its raw console reply and of
an original HCI capture. The lower controller/radio/security cause remains
unknown. Exact full-baseline restoration passes `0d5a9503`; the separate fresh
F12 original/host/released-lock review passes `a3454399`. This stop supplies no
journal, stale-response or corruption acceptance.

Fresh private `b38cde2e8de944e9b15986ceb55aec2c` retains the journal stages
and bounds while adding actual fresh exact-B advertising, passive HCI and USB
BLE STATUS originals around the single common Pair. Six checks pass normally
and with optimization. Its attempted launcher stops at the nested radio-source
admission before Backend creation, campaign creation or any target action:
the radio binding still names the preceding fixture/setup hashes. Independent
original stop review `18f6af5c` records zero new target operations; no Pair,
crypto or journal result exists. The earlier review did not exercise this
nested actual-main guard and remains historical evidence. Fresh packet
`1ecaa8e2e7f048eeb06458e7ee24f1a1` rebinds those two exact reviewed sources
and propagates only their dependent bindings. Seven checks pass normally and
with optimization, including actual-main admission reaching a denied
pre-endpoint sentinel; independent source review `80180a3a` is clear. This
repair supplies no journal acceptance. Its actual
`journal-pair-originals-live-013ca59f6e0343c19a971c62dc61a35a` run **STOPPED**
on `ModuleNotFoundError: check_usb_target`: the staged lazy USB dependency
closure is incomplete before BLE discovery, ENROLL or Pair. Zero journal
stages or jobs execute. Independent stop `7a1cda63`, exact full restoration
`dd306d3e` and separate fresh F12 `8b20a350` pass. The original stopped packet
remains unchanged.

Fresh source-only packet `1322b617cfcf4fa3bc073d7fbe96e86c` adds the existing
missing USB helpers to that exact staging closure while preserving case and
parent function bodies. Eight checks pass normally and with optimization,
including reproduction of the old missing import, real staged USB parsing
and default endpoint denial. Independent source review `5d70ec04` and
distinct campaign/action-lock review `0f97e378` are clear. Its actual
`journal-pair-originals-live-d2bb110b709a445e84a8724d56e730ed` run **STOPPED**
after fresh exact-B advertising, one ENROLL marker and one Pair attempt.
The retained passive HCI records show nominal connection completion followed
by remote-features status/disconnect `0x3e`, before any ACL/SMP/encryption;
the target's BLE counters remain zero. BlueZ reports Page Timeout. Successful
Pair, GATT identity, saved engineering seed, API writes and all journal stages
are unobserved. Independent stop `64176eb1` and diagnosis `21fb8267` establish
this boundary and leave the lower cause unknown; no blind Pair is proposed.
Exact full restoration passes `596af164`, and separate fresh F12 passes
`4c5ddf93`. The original stopped packets remain unchanged and add no journal
or cryptographic-refusal acceptance.

## Running-cookie owner grace

Campaign `sessions-bound-B-live-d7bf8cc3616f4605a7327a254586dd09` passes the
remaining declared running-owner grace subset, independently reviewed as
`7af95814`. The legacy engineering radio prefix passed in this execution;
no swapped-radio repair is required. The same expired cookie succeeds for
STATUS and ABORT while its inhibited job is running, then STATUS returns 401
after abort. The one job was declared for 45 seconds and deliberately aborted;
this does not prove a completed 45-second run. Fifteen original HTTPS
exchanges, 152 INFO samples, seven CRC-valid USB STATUS responses, one
lease-expired notification and inactive aborted-terminal records support the
bounded result. Exact full baseline restoration passes `baddebf9`; fresh F12
passes separately as `fbb744`.

Forbidden active mutations were not stimulated. The unchanged production
`LocalAccessController::softap_authorize` policy and the existing
`accelerated_session_deadlines` host check in `tests/field_access_tests.cpp`
cover expired running-owner LOAD refusal separately from this live result.
Commissioning-token negatives and other-carrier busy refusals do not qualify
that same-cookie target boundary. No additional live assertion or job is
added: the declared grace subset is retained, while whole B12R remains open
for planned composition/resources and consumer Save/STATUS overlap. Whole
session, resource, RF and physical timing closure is not claimed.

## Validation and independent reassessment

The retained private Linux batch contains all 1,701 paths from its recorded
committed revision with exactly three reviewed source/test overlays. It excludes
the unrelated dirty files,
untracked backlogs, credentials, backups and captures. The established retained
Linux workflow passes **155 selected tests, zero failures, 162 registered and
the same seven context exclusions**. Original configure/build/CTest logs and
archive membership were independently verified. No firmware, RF or device
acceptance is claimed from this run.

The current 271-entry source/cmake inventory has 270 entries unchanged from
`c0d2bd5`. Its one exception, `src/tools/phase12_flash_fixture.cpp`, is a host
native fixture linked only by the hardware-free `BUILD_TESTS` target. The
candidate firmware link closure is unchanged. Historical frozen runtime
bindings keep their recorded exact 271-file comparison; that historical
comparison is not a claim that all current entries remain unchanged.

Independent review found one ambiguity in the prompt's B12R limits. It is
resolved: the two-hour soak retains its own limits, while running-cookie work
has one 45-second simulator job and a 260-second body, and save/STATUS overlap
has one save/at most twenty STATUS requests per carrier/ten minutes. A stale
inert preparation command hash was also corrected before live execution.
Both source/config reassessments are clear. No speculative failure matrix was
added.

The exit observer's two added behavioral checks cover the observed busy-then-
complete sequence and persistent busy through the unchanged deadline. All
23 checks pass normally and with optimization, independently repeated by the
reviewer. This is a host observer repair, not a target radio diagnosis.

The maintained engineering discovery suites pass **88 normally and 88 with
optimization**, and the readiness suites including pending-proof ordering
pass **33 in each mode**. The final thirteen-path source reassessment
`424f83a3` is clear: **121 checks in each mode** is the sum of those separately
retained suites, not a claimed unified run. The unchanged native selection
remains 155 passed with seven context exclusions. The four frozen engineering packets add five
checks in each mode, including each actual controller prefix under denied
host/child/socket endpoints; 1,518 earlier artifacts retain their hashes.
These are source/admission checks, separate from the live results above.

Private original and review bindings:

- Linux archive: `68c3557ed8b113a2c009bcf3d046075c65aa9a01ea94a5f7944abfde8466dcce`.
- Linux summary: `4fc6b088a432b9947796deb261d89aa9475bf8950c85209524d1b1c75ba4b861`.
- Independent Linux original review:
  `0004a704491f3657aac588b44105a801a1b3dd905496124880ecce3337727dd0`.
- Corrected prompt/native source review:
  `29631f4fc21972233ac114f8ef466c05087efcd803afb2f14e2609a6bf161d91`.
- AP-before-boot source/actual-config review:
  `bba018e4eee40ed173fa330aa8e92f22e987200959f782c24a0f2355e5141c78`.
- Generation-8 cold network acceptance:
  `c50f5255958f244befc6a59a0acfea301591004b6a93d1bdf9275ce62aa7cf18`;
  independent F12 exit
  `360bb1760bdf89225d418534536cc2bda546509571b6f20c2818161f8294642b`.
- Pending-TLS stopped result:
  `943cb11ce9cf64e53770beb3144772cc938a7b6b6c79ed0163535010703ed4b8`;
  exact restoration
  `98b0420faff35d0eee287bbd775421b64d02358569fdba4bc775d709a788f18e`.
- Readiness source reassessment:
  `9e3feb23d30f7cbb6e4ff7b7d94f3b22b9e87fecf3eb523bafcdbd09da9f3c88`;
  discovery source/four-packet reassessment
  `cdb7a7e29b039a5bd927c6d9453735c838f37ffd0f3c81583ad1193b093a411b`.
- R11A original discovery stop:
  `17609f02e7c8b754310008ffc06a6d79dfdbc2e8cfbedb5d310a7a6d3876dcb7`;
  consumer host-binding reassessment
  `237e27035e285f1ba12e675c8b1bd8aff57064ec7644e32fb18f2f78b1841074`.

## Historical remaining execution and exit

Four automatic workstreams remained after C8T/R11F readiness and R11A automatic
criteria pass; the declared running-cookie grace subset is also retained. Operator
commissioning/offline browser use, independent indicator/GP14 timing, physical
power interruption, additional-peer capacity and RF/conditional production
qualification remain at the end. No operator inventory or RF readiness is
inferred. The three preexisting user paths remain excluded and byte-identical
to the starting preservation hashes. The nineteen-path publication scope is
fifteen owned source/test paths and four owned documents; current source
integration is independently clear as `c185d85b`. The publication receipt and
final report will record the eventual commit and independently verified remote
parity. The eventual commit hash is recorded outside this document.
F12 remains the recurring exit gate and is excluded from the four-workstream
count.

## Historical proposed operator block

The current [operator prompt](phase12-remaining-execution-prompt.md) supersedes
the earlier restoration and device-scope instructions in this block. Its named
physical evidence requirements are retained; the completed automatic work is
not repeated as setup.

Use the selected phone, iPad, laptop and B's existing GP14 wiring after fresh
F12. Root prepares the exact fixtures, observers and restoration first;
waiting for the operator does not start a timer. Accepted automatic saves and
fault stages are not repeated.

1. On the iPad, check saved-field prefill and perform the two predetermined
   network/station commissioning saves, one activation/reboot and exact
   readback per save, at most ten minutes each. On each iOS device used,
   disable cellular where available and show/reload B's isolated local portal
   and working cryptography without Internet; each visit has ten minutes.
2. Use the phone's supported offline Bluefy page for the prescribed identity
   exchange, then hold/release its actual BLE session while root runs the
   prepared additional-peer check. Use the Pi for the other peer once its engineering BLE prerequisite passes.
   The available devices cannot prove refusal of a fifth independent bond;
   app instances do not substitute for physical peers.
3. Observe the prepared LED/Identify priority sequence, at most five minutes
   per cue. Visible behavior does not prove precise edge timing or an injected
   indicator-write fault. Exact GP14 erase/program coincidence still needs
   the specified independent edge measurement.
4. Perform a physical power cut only for its exact prepared interruption
   fixture, one declared cut and at most two completion/resume boots within
   five minutes. The current completed-phase reset fixtures do not supply an
   in-pulse/torn-write trigger; do not improvise a cable pull as that proof.
5. RF is last and conditional on the current image/conducted receiver setup
   and one actual setup-bound Ready. That same one-use record covers preflight
   and acquisition within 300 seconds. Hold GP14 to ground for 12–15 seconds
   on the cue, release and show the same-boot phone portal within 90 seconds.
   Root runs exactly one 20-second Tone and 40-second IQ acquisition, requires
   independent cutoff/AP/latch evidence, then restores inhibited B and F12.
   Historical 17/12 preparation supplies no standing RF authority.

The existing [test-preparation packet](phase12-test-preparation-packet.md),
[time/LED plan](phase12-time-led-preparation.md),
[fault fixtures](phase12-fault-fixtures.md),
`scripts/gp14_flash_overlap.py` and `scripts/phase12_gp14_rf.py` retain the exact
fixture, timing and RF prerequisites. No extra equipment inventory or physical
acceptance is introduced here.
