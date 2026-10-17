# USB UTC uncertainty investigation

**Subsequent accepted policy:** WsprryPi now defaults new/missing WTP settings
to 100000000 ns (100 ms). Explicit saved values, including 1 ms, are preserved.
The [100 ms execution record](utc-100ms-results.md) covers product changes,
validation and review. The investigation below retains the original 1 ms
request, measurements and limitations; it does not claim 1 ms qualification.

Date: 2026-10-17. This follow-up corrects WsprryPi's USB measurement accounting
without changing WTP/1, Pico firmware timing, host clock configuration, saved
job limits or the Pi's 1000000 ns default. A 1 ms physical ARM qualification
is not claimed.

The final production client selected USB controller time in all ten no-network
observations. Submitted uncertainty was 17.686–18.235 ms; the subsequent
authoritative WTP clock reported 17.750033 ms after aging. Default 1 ms jobs
still refuse. The accounting defect is fixed; a 1 ms physical ARM outcome has
not been achieved and is not the recommended ordinary-operation requirement.

## Findings

The initial USB implementation bracketed the device capture with host clock
observations before the sample request and after its delivery ACK. Its UTC
midpoint therefore included an unrelated later ACK, and its error charged the
entire request/response/ACK interval. This was conservative about uncertainty
but unnecessarily wide and biased the midpoint toward the later ACK.

A finite inhibited Pico B check with no saved station Wi-Fi measured the
sample request/response separately at 20.77–21.52 ms and the subsequent ACK at
17.20–17.64 ms. Read-only kernel maximum error was 2.513–3.013 ms in those
observations. The old production client submitted 40.720548 ms uncertainty;
the Pico reported 40.722643 ms after clock aging. These values are different
observations from the earlier 56.7–71 ms RF-image acceptance, not a correction
to that historical evidence.

The foreground USB adapter processes at most 64 bytes per service step. The
JSON management exchange and delivery ACK each traverse multiple such steps
in the cooperative main loop. Its observed delay is not a USB hardware lower
bound. Even a perfect host UTC source cannot turn this roughly 21 ms sample
interval into evidence for a 1 ms uncertainty bound.

The host's currently selected PPS/Chrony source reported root distance and
remaining system correction in the tens of microseconds; kernel `adjtimex`
maximum error was sometimes larger. The production client continues to use
the conservative kernel bound. A small RMS offset or estimated error alone is
not a substitute for a qualified maximum-error estimate. Chrony's documented
system-clock estimate includes root dispersion, half root delay and remaining
system correction; see its [accuracy explanation](https://chrony-project.org/faq.html).

## Implemented accounting repair

WsprryPi now observes host UTC immediately before the sample request and after
the validated sample response, before sending ACK. The ACK remains mandatory;
an unconfirmed ACK never permits a submit. A separate observation after ACK
retains host qualification, regression and clock-step checks across that wait.
It does not recenter the old sample or charge ACK latency as transfer error.

If capture lies in `[t0, t1]`, the midpoint estimate has worst-case transfer
error `ceil((t1 - t0) / 2)`. This interval argument allows either direction to
consume all measured delay; it does not assume symmetric USB delivery. The
submitted uncertainty is:

```text
max(qualified host error before sample, after response, after ACK)
+ ceil(sample monotonic interval / 2)
+ absolute wall/monotonic discrepancy across sample and ACK
+ unchanged 100000 ns processing/drift margin
```

Clock-step, total exchange-age, overflow, leap, qualification, identity,
deadline and one-use sample checks remain. Pico still ages error from its
actual monotonic capture at the existing 50 ppm rate, including ACK/submission
time and time before job admission. No RF workspace, foreground service
budget, holdover, launch or uncertainty limit is weakened.

Runtime observations expose host uncertainty, sample round trip, midpoint
radius, total and post-ACK clock discrepancy, processing margin and ACK
duration. This separates the causes without claiming stronger clock quality.

The final exact-client component ranges were:

| Component | Minimum | Maximum |
| --- | ---: | ---: |
| Qualified host bound | 7.018444 ms | 7.021907 ms |
| Sample request/response interval | 21.131241 ms | 22.230775 ms |
| Midpoint interval radius | 10.565621 ms | 11.115388 ms |
| Total wall/monotonic discrepancy | 0 ns | 37 ns |
| Unchanged processing/drift margin | 0.1 ms | 0.1 ms |
| Separate ACK duration | 17 ms | 18 ms |

The kernel bound varies with its update/aging cycle: an earlier interval-fix
run had 0.017–0.515 ms host error and 10.168–11.212 ms submitted uncertainty.
The final run includes the additional post-ACK guard and a larger contemporaneous
kernel bound. Compare components rather than attributing every between-run
difference to USB code. These figures are conservative estimated uncertainty,
not independent measurements of actual UTC offset.

## The 1 ms requirement

Pi's 1 ms value originated as the default in its initial WTP production
settings (`2819f0b`). No waveform-derived rationale for making it a universal
requirement was found. WTP/1 requires enforcement of the explicit per-job
uncertainty and advertised device maximum; it does not prescribe a 1 ms value.
Pico currently advertises a 500 ms ARM maximum. Its existing standalone SNTP
calculation adds 1050999 ns before any round-trip delay, so even an ideal
zero-delay SNTP observation cannot satisfy the Pi's default 1 ms job.

Published WSPR guidance asks for clock accuracy on the order of one second;
see the [original WSPR description hosted by the WSJT project](https://wsjt.sourceforge.io/WSPR_QST_Nov_2010.pdf)
and the [WSJT-X clock checklist](https://wsjtx.github.io/wsjtx/guide-full.html).
This is an operational UTC reference, not evidence for electrical edge timing
or a reason to change relative symbol timing.

**Original recommendation, now accepted and implemented in WsprryPi:** for ordinary WSPR and the current slow
CW applications, use a 100 ms maximum estimated UTC uncertainty, checked at
ARM and again immediately before launch. This is an engineering policy target
with a tenfold margin against the published approximately one-second clock
guidance, not a published protocol requirement or an inference that every
100 ms observation has measured 100 ms actual error. Preserve all existing
local symbol timing, missed-start deadlines, lead time, cleanup and holdover
rules. Honor explicitly configured stricter values.

Keep 1 ms as an explicit precision operating requirement when there is a
demonstrated use case and a qualified clock-transfer path. Meeting it reliably
would require both a defensible sub-millisecond host UTC bound and a precision
transfer/capture design that excludes or measures device queue residence,
followed by target and independent timing qualification. A compact timestamp
exchange or a wired timing reference are proposals requiring that work, not
capabilities delivered by this accounting repair. Do not assume symmetric
one-way delay, drop kernel error, clamp the reported uncertainty, or relabel this
cooperative JSON path as 1 ms capable.

## Validation and physical scope

Linux USB management tests cover interval endpoints with fully one-sided delay,
odd-nanosecond rounding, a 200 ms ACK, missing ACK, pre/post-ACK clock steps,
clock regression, unqualified observations, overflow, cancellation and strict
framing/binding. The same cases pass AddressSanitizer/UndefinedBehaviorSanitizer.
The production Pi/Pico endpoint, application, persistence and protected-browser
wire fixture passes without network or hardware. Production runtime checks
and the existing UI runtime tests cover unchanged admission/reconciliation.

The bounded physical comparison uses Pico B USB serial `CDDBF8767C506C07`,
device `29f20b7342051ef947aa56cb9d4fab42`, on wspr5. It loads only the inhibited
normal image from the USB product source, label `9dee1ff177e6-dirty`, UF2 SHA
`e124be56b6819fae65cb124e8498052b9092868fd633df9ebd73828ce209e529`.
The [existing source manifest](usb-control-source-manifest.json) binds this
image to the committed Pico product. No Pico source behavior changes in this
follow-up; the dedicated Pi USB compatibility pin remains unchanged.

Two initial probes stopped on fixture issues (an unavailable volatile Wi-Fi
off operation and an omitted copied client). Both restored the original flash
exactly. Subsequent checks use the proven saved-network delete/restart path;
the temporary profile changes and firmware are always restored. No job is
armed and no transmitter RF, installed-service or absolute timing claim is
made. The Pico's SNTP source is not used for the no-network clock observations.

Final exact-client measurements and restoration are recorded in
[the sanitized result](usb-time-uncertainty-results.json). The final ARM64 client
SHA is `9f51d90d15ef278bef973348c2902f461fdd5ee537931ecc16603ae62e30b175`;
that record also binds the changed Pi source and fixture hashes. Original
firmware `7bff45c0f32f` and full-flash SHA
`02675b18ea96daca9ee52b95f41bd7f33dea0a5a739fee9fcc68e9e12cc73473`
are restored, output and scheduler remain inactive, and the installed Pi
service retains PID 390491. No running Pi binary, system clock or service was
reconfigured. The remaining 1 ms policy mismatch is
explicit; this repair does not claim that the original requested 1 ms physical
ARM outcome has been achieved.

The source and Pi documentation are committed and pushed as
`d43b4e305519fa4e1612c42c293849647d357e5c` on `devel`. Product CI runs separately
after publication; local checks above do not claim a completed new CI workflow.

## Reproduction and documentation impact

On a suitable Linux host with the existing dependencies, from WsprryPi:

```sh
make -C src wtp-usb-management-test WTP_NETWORK_BUILD_DIR=build/usb-time SUDO=
make -C src build/bin/wtp_production_test BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 src/build/bin/wtp_production_test
node WsprryPi-UI/tests/wtp_ui_test.js
node WsprryPi-UI/tests/wtp_usb_pair_test.js src/build/wtp-network/wtp_usb_pair_client /absolute/path/to/usb_management_driver
```

The native production runtime passes 447 checks. The same focused USB target
passes with `WTP_NETWORK_CXXFLAGS='-O0 -g -fsanitize=address,undefined
-fno-omit-frame-pointer'` and `WTP_NETWORK_LDFLAGS='-fsanitize=address,undefined'`
in a separate build directory. No native macOS Pi C++ build is attempted.
Compiler/Node image prerequisite differences are recorded in the Pi review;
the final native and Node commands both pass in their complete retained
environments.

Updated Pico USB protocol text and this investigation/evidence record, and
Pi's USB guide and development review. No frontend presentation changes are
made; the existing Node UI runtime regression passes. The separate operator
documentation repository remains outside the authorized write scope. The separately authorized [100 ms execution](utc-100ms-results.md) subsequently
updates Pi defaults, explicit UI adoption and policy validation. It leaves this
accounting repair and its original physical evidence unchanged. Operator
documentation in the separate repository remains a recorded follow-up.
