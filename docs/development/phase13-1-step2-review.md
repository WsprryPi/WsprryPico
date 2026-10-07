# Step 2 preparation, execution and adversarial review

## Disposition

Step 2 is **in progress**, not complete. Its comprehensive
[execution prompt](phase13-1-step2-prompt.md) is being executed on `devel`.
Independent preparation is complete within the recorded scope. The
[operator sheet](phase13-1-step2-operator-setup.md) groups the remaining physical
work into one untimed session, proposing B as DUT and A as the inhibited stop
fixture. Equipment availability, physical labels/accessories, wiring,
released-voltage evidence and optical capture remain unconfirmed. No operator
response deadline applies. Steps 3–6 remain open.

## Actual setup preparation

Control host `wspr5` reported Linux `6.18.34+rpt-rpi-2712`, approximately
338 GiB available on its persistent filesystem and only Pi `pispbe`/HEVC
processing video interfaces. USB inventory found both named Picos, the RSP1B
and the retained GPSDO. No optical camera was connected or identified. Video
device-node existence alone is not a camera-readiness result.

The existing tool hashes were verified:

| Tool on wspr5 | SHA-256 |
| --- | --- |
| `/home/pi/phase11-4-e1/picotool-build/picotool` | `4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921` |
| `/usr/bin/ffmpeg` | `8e227de186f3f53ec3c4624f6f75facb50ede5c0d2f59277d37a322093f91cfd` |
| Retained `complete-test-deployment-284c7e04a3fdd079c46e782b/wspq-capture-soapy` | `b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03` |

A three-second receiver-only smoke capture on **RSP1B `2404058C60`** retained
750,000 CF32 samples / 6,000,000 bytes. Actual settings matched the prepared
profile: 250 ksps, 200 kHz bandwidth, 3.55 MHz center, gain 20 dB, channel 0,
AGC and bias tee off. Metadata reports success and verified deactivate/close/
release, zero overflow and zero clipped samples. A separate file-size/hash
inspection matched IQ SHA-256
`ab19849bc4896f65f39ac50eb0a831fe0ab8afdc516785682afbf2265c84edbf`.
No receiver/camera helper remained running. This checks receiver collection;
it is not a transmitter or optical qualification result.

## Board authority, backups and return

The initial read-only Console inventory matched both identities/revisions,
empty state, inactive output, disabled schedules and unsynchronized time. The
legacy Console omitted owner/job IDs and active pin data. Both installed source
revisions were inspected: their native BOOTSEL handler requires actual unowned
reset permission and engine inactivity after local STOP and rechecks before
entering ROM. This gives a device-enforced quiescence grant without inferring
missing Console fields or enabling unsupported consumer USB WTP.

Under stable named-board locks and exclusive Console access, each firmware
accepted that guarded command. Serial-selected picotool read the full 4 MiB
flash twice; both readbacks were identical. The actual standalone journal
CRC/sequence/disabled configuration was validated and contained canonical
default pins: RF GP2, button GP14, onboard indicator, no other allocated roles.
Physical accessory attachments are still an operator input.

| Board / serial | Installed revision | Full-flash backup SHA-256 | Returned boot |
| --- | --- | --- | --- |
| A / `0BF4B4AEC9FFB344` | `6c7b14321003` | `12896dcebdf1bfffec9277cb531e0afdfb6ec37a42168cae8663b166edec5151` | `e83cac69de154245a974a3efdf5fc8af` |
| B / `CDDBF8767C506C07` | `58afb2735c23` | `5ce7c79005c32c737a04a47c42c5eec3349199651b023e919070b6a8eafb3da6` | `ee6a29625e539045a3230e5f3d36c196` |

No firmware load or journal rewrite was submitted. Both returned to their
original revision and configured station/schedules with schedules disabled,
empty state and output inactive. The reboots changed boot/time state and cleared
B's prior volatile safety latch; B then reported `rf_safety_inhibited=false`.
This is explicitly not restoration of the old volatile latch. No RF job was
submitted, no intentional GPIO stimulus was driven and RF admissions remain zero.

Fresh autonomous SNTP subsequently became available on both original images.
The exact already-approved step-1 source bundle completed normal Plain LAN
INFO/HELLO/STATUS/CAPS/GET_CLOCK inventory on both boards. WTP boot identities
matched Console; actual owner and job IDs were null, output inactive and schedules
disabled. Clock snapshots were synchronized, leap normal, with uncertainties
106,122,789 ns (A) and 77,988,888 ns (B). This closes the immediate stale-clock
inventory blocker for those observations, not long-term SNTP reliability.

Private local evidence is under ignored `build/phase13-led-step2/`, including
Console inventory, flash readback summary, receiver metadata/logs, independent
IQ checks and the after-reboot inventory. Raw full-flash backups and IQ remain
private on wspr5 under `/home/pi/phase13-led-step2-20261007/`. The original
inventory library's events remain private under its existing `/tmp/` staging
root; no repaired private source bundle was executed as a transfer workaround.
`setup-draft.json` uses a distinct preparation schema, `ready=false`, null camera
and unconfirmed physical inputs. It is deliberately not a runnable setup.

## Demonstrated finding and repair

The step-2 fixture assessment found that the planned 250 ms stimulus requests
reset on release: the real button policy uses under 400 ms for reset and 900 ms
held for stop. A behavioral regression using actual `ButtonDiagnostic`,
`ButtonRuntime` and RF-worker `ButtonSafety` reproduced the problem with the
old duration. It failed the no-reset assertion before the fix; evidence is
retained in `gesture-baseline-test.log`.

The inhibited fixture now uses a single declared **1,200 ms** duration for its
local release alarm. The real policy emits exactly one stop before release,
no reset and no AP setup request. Both the foreground and independent worker
policy are exercised. The alarm still releases to input, timer allocation
failure releases immediately, the fixture never drives high, and ordinary
firmware has no HOLD command. No manual timed hold is introduced.

Further review found that overlapping camera regions could assign one light
to several indicators and ordinary dictionary equality accepted `1` for the
`open_drain=true` fixture declaration. Setup validation now requires disjoint
regions and type-preserving fixture equality. Tests retain touching region
boundaries, reject overlap/invalid coordinates/changed hashes/typed fixture
substitution, reject the preparation schema as a run setup, and preserve
camera-independent recovery.

Storage assessment also found that the complete retained matrix needs 1,956
seconds of capture: IQ alone is 3,912,000,000 bytes, exceeding the 2 GiB `/tmp`
inventory staging filesystem. Preflight now reserves the entire matrix's
uncompressed IQ/video budget plus 10% and 256 MiB before board locks, snapshots
or ROM entry. Video is explicitly recorded as 8-bit `bgr0` FFV1 so the four-byte
pixel planning bound has a declared precision. Tests reproduce insufficient
temporary storage and verify refusal before any board operation. A persistent
source checkout/build directory is required; the observed persistent free space
is ample for the proposed 640×480/30 fps mode. Actual camera mode and capacity
remain to be frozen after equipment confirmation.

## Checks, reassessment and remaining operator work

The runner/setup tests passed **30/30** and the affected CTest group passed
**9/9**. ASan/UBSan passed the changed acceptance/gesture test; normative WTP
validation passed (23 schema, 7 raw JSON, 1 framing and 8 transition cases).
Changed C++ formatting, Python syntax, whitespace, documentation links and
private artifact permissions were checked. Exact clean candidate binding is
refreshed after the source commit and recorded in the private build log and
final task report. The earlier full-host baseline's two unrelated failures
remain documented in the step-1 review; this slice did not change those paths.
The second assessment covers actual gesture thresholds, reset/release states,
GPIO/physical-pin confusion, inactive biases, ownership and source binding,
ROI geometry, recording independence, false readiness, bounded process cleanup
and original-image return. No actionable source finding remains in this
preparation slice after the repairs and affected retests. Software fixes do not validate the assembled circuit,
camera, optical edge timing or electrical stimulus. Those physical inputs remain
pending; they are not reclassified as software passes.

The operator sheet must be confirmed and recording/measurement checks performed
before marking step 2 complete. The equipment question remains pending. A real
camera mode/identity/view, both LED circuits, common ground/stop wiring and
released-level evidence cannot be manufactured remotely. Exact RF/LED edge
qualification additionally needs appropriate independent measurement; missing
equipment or an unaccepted timing scope remains explicit. There is no countdown
or request to observe a transient signal while a test runs.
