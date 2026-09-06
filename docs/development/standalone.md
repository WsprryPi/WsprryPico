# Standalone configuration and timing

Status: Step 9 software and the [inhibited Wi-Fi bench slice](standalone-physical-validation.md)
are validated on the recorded device. Conducted standalone operation, Wi-Fi
reconnection under RF load, separate-power boot, flash brownout behavior and
calibrated UTC/RF accuracy remain open. The original
[execution prompt](step9-standalone-execution-prompt.md) defines the software;
the [physical prompt](step9-physical-execution-prompt.md) records the later scope.

## Images and shared service

The standard `WsprryPico` image now includes persistent configuration, autonomous
Wi-Fi SNTP and an inhibited local lifecycle simulator. It never enables the RF
output. The simulator permits foreground observation of a scheduled start within
the configured uncertainty; its completion is a software diagnostic, not evidence
of physical timing. It advertises `inhibited-standalone-simulator`.

Explicit target `WsprryPico-StandaloneRF` uses the existing experimental 138 MHz
PIO/DMA GP2 engine. Only that image joins persistent schedules to physical RF.
It advertises `pio-dma-gp2`; both images expose `wspr` and `tone` WTP jobs with the
existing four tone requests starting at 3,570,100 Hz, spaced 1.464843750 Hz.
This is experimental scope, not supported-band or output-power qualification.
The separate `WsprryPico-RFBench` and USB-time `WsprryPico-RFWTP` remain available.

Standalone and USB WTP share one `JobService`. The scheduler claims a distinct
local principal, encodes a complete Type 1 WSPR job, then LOADs and ARMs it. It
never steals an external ownership lease, depends on a USB connection, or sends
per-symbol requests. USB disconnect does not invalidate SNTP time. WTP/1 itself
is unchanged. HTTP, browser APIs, TCP control, DNS, SoftAP and BLE provisioning
remain later work; Wi-Fi here supplies DHCP and a UDP time client only.

## Configuration

One-time configuration uses the **Console** CDC interface, not WTP. Send a single
ASCII line `CONFIG ` followed by the complete JSON document and a newline.
The administration commands below share this interface. Send one command at a time and wait for
its JSON response; diagnostics use the bounded existing Console queue. A client
must inspect `ok`, not assume a successful serial write saved anything.

Sanitized document (replace all station/network fields before using it):

```json
{
  "version": 1,
  "enabled": false,
  "station": {"callsign": "K1ABC", "locator": "FN42", "power_dbm": 20},
  "wifi": {
    "ssid": "YOUR-NETWORK",
    "password": "YOUR-PASSWORD",
    "ntp_ipv4": "192.0.2.1"
  },
  "schedules": [{"period_s": 600, "phase_s": 0}]
}
```

`192.0.2.1` is a documentation placeholder, not a public time service. Configure
a trusted reachable numeric unicast IPv4 NTP server. Wi-Fi currently accepts a
printable ASCII SSID (1–32 bytes) and WPA2 AES passphrase (8–63 bytes); open,
enterprise, WPA3-only and raw hexadecimal PSK provisioning are not implemented.
Keep local credentials in ignored `config/local/` or another private location.
Credentials are stored in flash without encryption, but never returned by
`STATUS` or included in maintained firmware build inputs. Configuration is
physical-console administration, without a remote authentication protocol.

The document is limited to 1,800 bytes and eight schedules. Station validation
uses the existing strict uppercase callsign, four-character Maidenhead locator
and supported exact WSPR dBm values. The dBm value is encoded message content;
it does not set or measure physical output power. Unknown or duplicate fields,
noncanonical numeric types, unsupported versions and intersecting schedules are
rejected. Schedules require an even-minute `period_s` from 120 through 86,400,
dividing one day exactly. `phase_s` is an even-minute offset less than the period.
The occurrence is `UTC period boundary + phase_s + 1 second`, with no local time
zone or daylight-saving interpretation.

A new/erased device has no configuration and cannot schedule. Saving requires
an idle unowned service and verified flash writes. It returns `reboot_required`
and suspends standalone admission until reboot applies the saved
network settings. USB WTP remains usable. An enabled saved configuration in an
RF-capable image can transmit after reboot as soon as its time and schedule
conditions pass. Saving `enabled:false` prevents further standalone admissions;
configuration changes do not abort an owned active job. Use its WTP owner to
abort or wait for completion before editing configuration. For a locally owned
standalone job, Console `STOP` aborts it and suspends further local admissions
until reboot. It does not abort an external WTP owner.

`STATUS` reports saved station/schedules, enabled state, storage health, required
reboot, latest reservation, clock state/uncertainty, engine, current service
state, last admitted job ID and the last admission error. Runtime terminal
reasons remain available through WTP STATUS and its retained terminal records.
Wi-Fi credentials are omitted entirely.

## Bounded administration and recovery

Optional `expires_utc_s` is a UTC seconds integer in the supported era; omitted
or zero preserves the unbounded schedule configuration. A nonzero expiry skips
any occurrence whose nominal full WSPR frame would finish after that time.
The bench client requires explicit `--enable-schedule` and an expiry within one
hour before provisioning an enabled schedule.

`INFO` adds device/build identity, recovery diagnostics, network link state,
SNTP counters and latest correlated RTT/sample uncertainty. It includes the
sanitized schedule status; RF images also report launch and DMA diagnostics.
`REBOOT` and `BOOTSEL` first stop local scheduling, require unowned idle state,
verify inactive output, then reset. The inhibited image additionally offers
`WIFI OFF` and `WIFI ON` while idle for controlled network-loss testing.

Use `scripts/standalone_console.py ACTION --port DEVICE --device-id ID --run`.
Configuration also requires `--revision REV --config PRIVATE_JSON`; the tool
checks device identity before issuing the command and never echoes credentials.
Capture INFO and image hashes before a campaign. Closing a USB port proves no
per-job commands, but is not evidence of physical power-only operation.

An eight-second watchdog recovers foreground stalls into a boot that suspends
local schedules and skips networking. Intentional Console reboot starts a normal
boot. Recovery reports the failed stage and retained panic/processor diagnostic
values; it does not automatically clear credentials, watermarks or faults.

## Time policy

The original portable parser implements a restricted unicast SNTPv4 exchange;
[the NTPv4 specification](https://www.rfc-editor.org/rfc/rfc5905.html) defines the
packet format. This implementation is not a full NTP selection/discipline
algorithm or an authenticated time service. It trusts the configured server and
network; peer matching and a random origin token are correlation checks, not
cryptographic authentication. Do not use a leap-smearing source as ordinary UTC.

The Pico adapter validates the configured peer address and UDP port 123. The
parser requires a 48-byte version-4 server reply, matching one-shot origin token,
stratum 1–15, normal leap indication, valid ordered receive/transmit/reference
timestamps, reference age at most one day, acceptable precision and root
metrics, and at most one second local RTT. Pending or unknown leap indications
invalidate time. A correlated stratum-zero kiss-of-death invalidates time and
stops queries to that server until reboot. Invalid/stale replies never refresh
an observation. UTC is explicitly restricted to 2025–2099, including the 2036
NTP era rollover; a zero NTP timestamp remains the invalid sentinel.

The estimate uses server transmit time plus half the RTT remaining after server
processing. Its uncertainty includes the **full** local RTT, half the server's
root delay, root dispersion, a local/drift margin and up to 999 ns of mapping
quantization. The UTC-to-monotonic offset is on the RP2350 microsecond timer grid
so an exact UTC WSPR slot produces a representable hardware alarm. Observations
above 500 ms uncertainty are rejected. This user-selected budget replaces the
initial 20 ms policy and retains margin against the approximately one-second
clock guidance in the [WSPR description](https://wsjt.sourceforge.io/WSPR_QST_Nov_2010.pdf).
Admission and launch both enforce 500 ms including oscillator aging. The assumed oscillator bound is 50,000 ppb,
not a measured oscillator calibration; uncertainty grows with age.

Network polling is foreground-only. Connection attempts are separated by 30 s;
queries by 64 s. Startup requires neither a USB host nor a wall-clock seed. The
clock is synchronized for at most 90 s and enters holdover through 180 s, but
this image admits/launches jobs only with source age at most 90 s and uncertainty
at most 500 ms. An outage can skip slots; no schedule is guaranteed to transmit.
RF frequency correction is separate and is not inferred from SNTP observations.

## Scheduling, flash and failures

The scheduler considers a future occurrence only 2–10 seconds ahead. It never
catches up missed slots. A global persisted UTC watermark is reserved **before**
engine preparation; attempts that fail afterward are skipped, even across a
reboot. A backward UTC step cannot repeat any reserved or earlier occurrence.
Changing schedules or station identity does not reset the watermark. A large
erroneous forward clock step can therefore suspend scheduling until UTC catches
up or an operator deliberately resets storage; this favors no repeats over
availability. This is an at-most-once attempt policy, not guaranteed delivery.

Four 4 KiB sectors at flash offsets `0x3fb000`–`0x3fefff` are reserved in every
maintained image. The final sector (`0x3ff000`–`0x3fffff`) is separately
reserved for the RP2350-E10 boot workaround, observed in its last page.
The initial, physically unvalidated layout overlapped that page and failed
closed on this board. It must not be used for persisted configuration.
Two sectors hold 2,048-byte configuration records; two hold
256-byte watermark records. Each contains a format magic, 64-bit sequence,
length, payload and four-byte IEEE CRC32. Journal magic `WWPSTOR2` identifies
the corrected layout independently of JSON configuration version 1. Old-layout
records are rejected, even with valid checksums; no automatic migration can
safely drop the old final watermark bank. The next bank is erased only when the
current bank is full; a complete verified current record exists before that
rotation. Writes are verified before acknowledgement and happen only outside
armed/running jobs. Flash accesses use the SDK's single-core safe routines with
interrupts masked; core 1 and background Wi-Fi servicing are not used.

CRC32 detects torn writes and accidental corruption; it is not a security MAC.
A non-erased invalid record in **either** journal latches a storage fault. The
firmware does not silently restore an older enabled configuration or ambiguous
watermark. Torn writes can therefore require operator recovery. Recovery is a
separately authorized full-device flash erase in BOOTSEL, followed by reflashing
and reprovisioning; this clears credentials and the no-repeat history. A normal
UF2 update preserves the reserved region. Do not erase storage as an automatic
response to a CRC error. Future storage-schema changes require an explicit
migration design, not reinterpretation of old records.

At the maximum two-minute schedule, watermark storage programs 720 pages/day,
with about 45 sector erases/day shared between the two banks. This is 16
reservations per erase, rather than one erase per job. Flash endurance and
brownout behavior need device-specific qualification; no lifetime claim is made.
Configuration writes are administrative, not performed on each network sample.

Foreground service refills RF before other work. Wi-Fi polling is suspended
throughout an armed/running job, so networking cannot block DMA refill or the
launch guard. The already accepted clock observation ages locally. USB WTP
remains serviced, including ABORT. Wi-Fi resumes after the terminal state and
can reacquire time before a later slot. Physical resource coexistence, access
point behavior during that pause and underflow margins still require target
measurement on the final image.

## Reproduction and evidence

Hardware-free commands:

```sh
cmake --preset host-debug
cmake --build --preset host-debug --parallel
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake -S . -B build/step9-sanitize -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/step9-sanitize --parallel
ctest --test-dir build/step9-sanitize --output-on-failure
cmake --preset pico2-w
cmake --build build/pico2-w --target WsprryPico WsprryPico-StandaloneRF \
  WsprryPico-RFWTP WsprryPico-RFBench rf_driver_linkcheck --parallel
python3 scripts/check_standalone_image.py build/pico2-w/firmware/WsprryPico.elf
python3 scripts/check_standalone_image.py build/pico2-w/firmware/WsprryPico-StandaloneRF.elf
```

The initial software validation passed all 17 configured host tests (including the existing
optional offline analysis/USB descriptor checks), all 13 sanitizer-build tests,
and the WTP contract validator. All five named Arm targets cross-linked against
the pinned SDK/toolchain. Image inspection checks the 16 KiB stack, heap
separation, reserved flash region and UF2 payload extents. These commands do not
flash, connect to hardware or operate a transmitter.

New tests cover strict configuration, every byte interruption of configuration
and watermark writes, bank rotation interruption, CRC corruption, restart
retention, repeated/backward slots, competing USB ownership, busy edits, failed
reservation/preparation, time uncertainty/loss, malformed SNTP, replay, leap and
era boundaries. An end-to-end host test supplies SNTP time to the actual
discipline and scheduler, verifies a microsecond-aligned launch mapping,
completes an inhibited job without USB input, then skips further work on time
loss. A simulated completion is not a conducted RF result.

## Initial software adversarial assessments

The first assessment repaired the SDK linker-override invocation, replaced
unnecessary SHA-256 storage hashing with CRC32, and made corruption inhibit
instead of restoring an older enabled configuration. It also caught the
unrepresentable fractional SNTP-to-alarm mapping; quantization is now explicit
and included in uncertainty. The standard inhibited image uses a named lifecycle
simulator so it does not depend on foreground polling at one exact nanosecond.
Firmware classification, new dependency provenance and timer/holdover limits
were checked and corrected. Affected host checks and target builds were rerun.

The follow-up assessment checks the completed implementation against the prompt,
including stored disable state, erase interruption, no-repeat behavior,
lease expiry through a frame, failed preparation, integer/era bounds, source
correlation, clock loss, flash/RF exclusion, secret-free status and the actual
linked memory layout. Target qualification limits remain explicit. Review and
validation results here apply to software and build evidence only.

After repairs and repeated affected checks, the final assessment found no
remaining actionable software findings in this slice. Physical qualification
items above remain open and were not reclassified as software passes.

The later [physical validation record](standalone-physical-validation.md) documents
the boot-page overlap, corrected journal identity, network alignment, recovery
controls, expanded checks and the user-selected 500 ms UTC uncertainty budget.
