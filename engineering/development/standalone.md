# Standalone configuration and timing

Persistent carrier calibration uses the independently advertised
`/api/v1/rf-calibration` resource. Saved manual correction is signed ppb with
zero/manual default and decimal ppm presentation; saves take effect only at
future preparation. RF correction uses manual PPM only; μChrony controls UTC.
The [UTC/RF contract](clock-discipline.md) defines manual-only RF
calibration and removal of the Pico-to-Pi GPIO timing link.

Current [Hostname selection](hostname.md) uses the saved consumer profile name for a new boot while keeping the running boot coherent. The editor does not require message/job entry, alter station/schedule readiness, clear STOP, or change pins/watermarks. Engineering names require replacement matching credentials.

## Images and shared service

The standard `WsprryPico` image includes persistent configuration, autonomous
Wi-Fi SNTP, USB management/time and the existing 138 MHz PIO/DMA GP2 RF engine.
It advertises `pio-dma-gp2`. RF capability does not itself enable transmission;
saved configuration and all ownership, timing, frequency and output guards apply.
The explicit compatibility target `WsprryPico-StandaloneRF` uses the same wiring.

Optional [amplifier enable](amplifier-enable.md) initializes inactive
from the validated boot plan and asserts only at the final local RF launch.
It remains enabled across that job's keyed gaps and deasserts when RF stops;
the two finite frames of a Type 2/3 pair have separate enable intervals.
Completion, cancellation and faults share local cleanup. No lead/tail delay is
applied. The inhibited image initializes a configured output inactive and never
asserts it for a simulated job. Pin/polarity saves require explicit restart and
retain the existing sticky hardware inhibition, including A/B/A saves.

Explicit `WsprryPico-Inhibited` selects the local lifecycle simulator. It never
enables RF output, reports `inhibited-standalone-simulator`, and its linked image
is checked for absence of the physical engine/worker. Simulated starts and
completions do not establish physical timing. Both variants expose finite
`wspr`, `tone`, `qrss`, `fskcw` and `dfcw` jobs with the existing 512-event,
3600-second capacity, 100 kHz through one Hz below half the selected sample rate.
See [build commands and target selection](firmware-foundation.md).
Autonomous WSPR schedules use an explicitly saved whole-Hz base frequency,
configured at runtime through the consumer settings page or the independently
versioned `/api/v1/standalone-frequency` resource. Firmware images select no
transmit frequency and contain no enabled station schedule. An older record
without a saved frequency remains readable but cannot claim, prepare or arm
an autonomous job. Its first explicit frequency save leaves schedules disabled;
the operator must enable them deliberately. An already configured frequency
change applies to the next job without a firmware rebuild or restart. Both
frames of a Type 2/3 pair retain one frequency snapshot.

`STATUS` reports the selected base in nanohertz, or null when unset, together
with `frequency_required`. Legacy application resource projections use the
nontransmitting decimal-string sentinel `"0"` when unset. Generic updates
preserve explicitly saved frequency; older firmware may reject the new optional
stored field, so downgrade preservation is unqualified. Explicit physical
Console `CONFIG` may supply `wspr_base_frequency_hz` in whole Hz; omitted legacy
writes preserve its saved value. No build-time band selection remains.
This is experimental scope, not supported-band or output-power qualification.
See [clock limits](clock-support.md) and [band support](band-support.md) for
frequency admission and conducted applicability.
The separate `WsprryPico-RFBench` and USB-time `WsprryPico-RFWTP` remain available.

The application images also enforce the saved experimental frequency policy
below before engine preparation. Numeric capabilities describe representability;
they do not bypass the application policy or establish supported-band status.
The separate diagnostic bench images retain their explicit experimental,
numeric-only scope and do not consume the application configuration.

Standalone and USB WTP share one `JobService`. The scheduler claims a distinct
local principal, freezes an automatic Type 1/2/3 WSPR plan, then LOADs and ARMs each complete frame. A Type 2/3 pair retains one local ownership lease across its RF-off gap. It
never steals an external ownership lease, depends on a USB connection, or sends
per-symbol requests. USB disconnect does not invalidate SNTP time. WTP/1 itself
is unchanged. Authenticated HTTPS/browser APIs and WTP/TCP now share this service;
see [network control](network-control.md). The
[Field access](field-access.md) defines engineering BLE and SoftAP
local control through this same service. Consumer commissioning follows
[consumer access](consumer-lan-access.md). General physical/fleet interoperability
remains unqualified.

## Configuration

Engineering Console configuration uses its own CDC interface, separate from
WTP. Current [USB management](usb-local-configuration.md) also configures shared
resources without Wi-Fi, while consumer network identity/Wi-Fi changes use
transactional setup and radio changes use authenticated Consumer-Radio.
Send a single ASCII line `CONFIG ` followed by the complete JSON document and a
newline. The administration commands below share this implemented interface.
Send one command at a time and wait for its JSON response; diagnostics use the
bounded existing Console queue. A client must inspect `ok`, not assume a
successful serial write saved anything. `ACCESS SOFTAP <full-device-id>` now
requests an initial 120-second SoftAP join window while access
storage is healthy. A connected Wi-Fi client retains the AP; the final disconnect starts a ten-minute inactivity interval. The command neither changes credentials nor authorizes the browser;
the page still requires the local-access password.

Sanitized document (replace all station/network fields before using it):

```json
{
  "version": 1,
  "enabled": false,
  "station": {"callsign": "K1ABC", "locator": "FN42", "power_dbm": 20},
  "wifi": {
    "ssid": "YOUR-NETWORK",
    "password": "YOUR-PASSWORD",
    "ntp_ipv4": "pool.ntp.org"
  },
  "schedules": [{"period_s": 600, "phase_s": 0}]
}
```

`pool.ntp.org` is the default for initial configuration, Console CONFIG and
explicit replacement with omitted `wifi.ntp_ipv4`. Ordinary API PUT preserves
the saved omitted time-server value. The browser prefills this default when no saved configuration
exists. Explicitly saved servers are preserved; empty or invalid values are rejected.
You can select another reachable NTP server by DNS hostname or canonical unicast IPv4 address.
The version-1 JSON key `ntp_ipv4` is retained for stored/config-client compatibility,
but now accepts either form (up to 253 ASCII characters; labels 1–63 characters,
letters/digits/hyphens, no leading/trailing label hyphen). A terminal root dot
and DNS case are normalized at runtime. `.local` uses a legacy unicast-response
mDNS lookup. The browser labels this field **Time server**. Wi-Fi currently accepts a
printable ASCII SSID (1–32 bytes) and WPA2 AES passphrase (8–63 bytes); open,
enterprise, WPA3-only and raw hexadecimal PSK provisioning are not implemented.
Keep local credentials in ignored `config/local/` or another private location.
Credentials are stored in flash without encryption, but never returned by
`STATUS` or included in maintained firmware build inputs. Configuration is available through Console or authenticated browser management.

Two optional top-level JSON booleans match WsprryPi's advanced settings:

| Setting | Default | Effect |
| --- | --- | --- |
| `allow_unqualified_frequency` | `false` | Permit an untested or failed amateur band within the engine's actual limits. |
| `allow_non_amateur_frequency` | `false` | Together with `allow_unqualified_frequency:true`, permit frequencies outside the recognized amateur-band correlation ranges. |

Set these with a complete engineering `CONFIG` document where the saved profile
permits Console configuration, or authenticated
`PUT /api/v1/config`, for example by adding
`"allow_unqualified_frequency": true` to the sanitized document above. For a
non-amateur experiment, also add `"allow_non_amateur_frequency": true`.
Initial configuration, Console CONFIG and explicit API replacement default
omitted flags to false. Ordinary API PUT preserves saved omitted flags; send
explicit false to revoke them. Strings, numbers, null and duplicate fields reject.
False settings are omitted from canonical storage/readback to preserve legacy
default configuration bytes. `STATUS` reports both effective booleans. A full
configuration replacement that omits a flag revokes that opt-in. Ordinary
browser form saves, station-only, hardware-only and schedule-only updates
preserve saved opt-ins. These advanced settings are outside the ordinary form.
See the [configuration-update contract](configuration-updates.md) for atomic
merge/replacement, preserved optionals and the explicit compatibility migration.

The optional `gpio_drive_ma` selects 2, 4, 8 or 12 mA on the direct RF pin,
with explicit 4 mA default. It is independent of reported WSPR dBm and measured
RF power. Legacy API saves preserve omission; drive-aware config/3 and update/3
accept explicit values. Console CONFIG, initial creation and deliberate
replacement default omission to 4. Saved, immutable boot and nullable cached
pad verification are separate; saving never programs a pad. See
[GPIO drive](gpio-drive.md) for restart, progress and downgrade semantics.

Changes to the two frequency-policy flags require the existing idle, unowned
configuration boundary and apply to the next new job without reboot, unless
another restart latch blocks admission. They persist in the existing configuration
journal and do not reset its separate transmission watermark. USB WTP, LAN WTP,
BLE/local browser jobs, compiled `LOAD_MESSAGE` jobs and autonomous schedules
all enter the same application policy. Every RF-on event and any realized engine
adjustment is checked; a disallowed mark or space rejects LOAD with
`FREQUENCY_REJECTED` before ARM. `allow_frequency_adjustment` remains a separate
per-job consent to engine quantization.
WsprryPi's host opt-ins do not automatically change the Pico's saved settings;
an experiment must satisfy both members' admission policies.

Default admission retains the thirteen ordinary bands from 2200 m through
6 m. The broad 8 m and 5 m correlation envelopes remain
experimental and require `allow_unqualified_frequency`. [Point-scoped qualification](band-support.md) covers only Pico A at 40.001 and
60.001 MHz, normal 138 MHz, with explicit WSPR receiver-audio conditions and
complete-job/admission conditions. It does not promote either whole envelope.
The ordinary consumer profile uses its authenticated radio configuration API;
it deliberately rejects Console configuration. False flags may be absent from
canonical Config readback; STATUS exposes their effective values.
4 m remains Unqualified
for every release mode under the required reliable-WSPR gate, and native direct
2 m is Unavailable. See the [qualification catalog](band-support.md)
and [machine-readable statuses](band-support.json). Experimental consent
does not change qualification, promote prior failed results or override engine
availability. Correlation
envelopes match WsprryPi's Band-Lookup catalog and are not jurisdiction-specific
operating authority.

Neither flag overrides an unavailable engine, numeric frequency limits, mode,
event or duration limits, clock, ownership or output safety checks. Direct 2 m
synthesis remains outside all current clocks' limits; these settings add no
native harmonic mapping. At 150 MHz a 4 m experiment can be admitted with
explicit unqualified consent, while 132/138 MHz direct-synthesis bounds still
reject it. The RF-inhibited application uses the same admission policy for
diagnostics and continues to generate no physical output.

An experimental 2 m signal needs a manually prepared third-harmonic job at a
lower fundamental, with the job's tone spacing also divided by three. A
fundamental around 48.16 MHz is outside this correlation catalog and requires
both flags. Supplying a normal 144 MHz job still fails the numeric limit;
neither flag converts it into a harmonic job. This is experimental use and
does not restore release support for 2 m.
Its failed WSPR pilots remain Unqualified evidence; native 2 m stays Unavailable.

The document is limited to 1,800 bytes and eight schedules. Station validation
uses the existing strict uppercase callsign, four- or six-character Maidenhead locator
and supported exact WSPR dBm values. The full locator is saved, and the existing
Type 1 frame uses its first four characters. The dBm value is encoded message content;
it does not set or measure physical output power. Unknown or duplicate fields,
noncanonical numeric types, unsupported versions and intersecting schedules are
rejected. Schedules require an even-minute `period_s` from 120 through 86,400,
dividing one day exactly. `phase_s` is an even-minute offset less than the period.
The occurrence is `UTC period boundary + phase_s + 1 second`, with no local time
zone or daylight-saving interpretation.

Saved callsigns accept 3–12 uppercase letters/digits and nonempty slash-separated
prefix/suffix segments, with at least one letter and digit. An extended callsign
is preserved in storage and readback. The automatic WSPR planner supports Type 1, Type 2 and Type 3. Ordinary calls
retain Type 1 with the first four locator characters on air. A supported
compound call uses Type 2 with a four-character locator, or Type 2 then Type 3
with a six-character locator. Explicit `<CALLSIGN>` requests Type 3 only and
requires six locator characters; brackets count toward the 12-character stored
token bound and are excluded from the hash. Supported affixes are one to three
alphanumeric prefix characters, one alphanumeric suffix character, or two
numeric suffix characters, attached to an encodable ordinary base call.
Unsupported legacy slash identities remain readable but report `UNSUPPORTED_MODE`
before claim/reservation. No identity is stripped, truncated or substituted.

Type 2 carries no locator. `/Q`–`/Z` overlap `/00`–`/09` in its payload: both
forms are supported, with the alternate full call and ambiguity exposed in the
versioned plan. A receiver may choose the alternate. Type 3 hashes the requested
full identity; a hash is not a plaintext announcement and receiver context is
needed. Encoding success does not establish receiver resolution.

A pair occupies adjacent even-minute windows, each starting at +1 second.
Each frame has 162 symbols and lasts 110.592 seconds; its RF-off gap is 9.408
seconds and the whole pair spans 230.592 seconds. Before the first LOAD/ARM,
the durable watermark reserves through the second window, consuming intersecting
configured recurrences. Both complete frames must fit expiry. Separate finite
jobs retain one renewed lease across the gap and receive independent launch
clock checks. STOP, lost ownership/time quality, changed configuration, missed
second preparation, engine failure or reboot cancels continuation without retry.
Reboot and UTC rollback conservatively skip both reserved windows. See the
[WSPR planning contract](wspr-planning.md) for source-specific software
acceptance and remaining physical qualification.

A new/erased device has no configuration and cannot schedule. Saving requires
an idle unowned service and verified flash writes. `reboot_required` covers
boot-network differences, external profile restart requirements and the sticky
pin/drive hardware latch. Changing pins or drive saves without applying hardware
and inhibits output until restart, including A/B/A saves; returning to the
boot value cannot clear that latch. Station, power, enabled and schedule changes
affect subsequent admissions when no restart/fault gate blocks them. An already suspended STOP stays
suspended. A network-enabled device can restart through the browser while idle. USB WTP remains usable. An enabled saved configuration in an
RF-capable image can transmit after saving or reboot as soon as its time and schedule
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

Optional `expires_utc_s` is a UTC seconds integer in the supported era; zero
means unbounded. Ordinary API PUT preserves omitted expiry. Initial setup,
Console CONFIG and explicit replacement default omission to zero. A nonzero expiry skips
any occurrence whose nominal full WSPR frame would finish after that time.
The bench client requires explicit `--enable-schedule` and an expiry within one
hour before provisioning an enabled schedule.

`INFO` adds device/build identity, recovery diagnostics, network link state,
SNTP counters and latest correlated RTT/sample uncertainty. It includes the
sanitized schedule status; RF images also report launch and DMA diagnostics.
`saved_consumer_profile` is a redacted view of the consumer journal selected
at boot: station callsign/grid/power, saved SSID/time server, owner count/epoch
and request SHA-256. It is `null` for other sources and on failed admission.
Bind it to the outer device ID, `provisioning_source` and generation; it does
not assert clock/TLS readiness or expose passwords, keys or client material.
The nested `status.station` still describes the separate standalone store.
Consumer save acceptance uses the new readback after activation restart;
an unknown pre-restart result requires journal reconciliation.
`REBOOT` and `BOOTSEL` first stop local scheduling and require an unowned,
inactive state. A latched failure is eligible only when storage is healthy and
autonomous scheduling is persistently disabled. The engine must then disable
successfully and confirm inactive output before reset. This explicit Console
recovery does not let WTP requests clear a fault or steal an owner. The inhibited image additionally offers
`WIFI OFF` and `WIFI ON` while idle for controlled network-loss testing.
The maintained images request and read back no-power-save mode at startup and
Wi-Fi re-enable so a USB-powered network controller continuously receives LAN
traffic. This trades radio power consumption for reachability; electrical power
and RF timing effects require their own measurements.

Use `scripts/standalone_console.py ACTION --port DEVICE --device-id ID --run`.
Configuration also requires `--revision REV --config PRIVATE_JSON`; the tool
checks device identity before issuing the command and never echoes credentials.
The bounded diagnostic actions include `info`, `status`, `storage`, `netlink`,
`access-status` and `ble-status`. Device-bound local actions include `softap`
and `identify`; the helper appends the already checked full device ID rather
than accepting an independently typed command payload. Existing `stop`,
`abort`, `reboot`, `bootsel`, `wifi-off` and `wifi-on` actions retain their
documented administration semantics.
Capture INFO and image hashes before a campaign. Closing this client leaves no
per-job commands from it; physical USB absence is stronger evidence that no USB
host can control the device.

USB Console retains physical administration/recovery commands, and the separate
USB management/time interface supplies shared JSON settings and qualified UTC
without Pico networking. Optional
[network control](network-control.md) now supplies authenticated HTTPS status and
management alongside WTP/TCP; it does not expose the physical Console override.
Wi-Fi also supplies SNTP. With a separate USB
power supply, a receiver can verify scheduled RF and independently decode the
station message. After a power change back to the Mac, INFO can verify retained
configuration and the schedule watermark, but the new boot resets live counters
and terminal status. The watermark records a reservation, not proof that RF
completed; pair it with receiver evidence for conducted RF work. Inhibited
network acceptance uses authoritative WTP results without an RF claim.

An eight-second watchdog recovers foreground stalls into a boot that suspends
local schedules and skips networking. Intentional Console reboot starts a normal
boot. Recovery reports the failed stage and retained panic/processor diagnostic
values; it does not automatically clear credentials, watermarks or faults.

The access-recovery operation is separate: it clears local
password/bond state, increments the access epoch, restores the public default,
sets persistent field mode, opens one confirmed volatile enrollment window,
forces SoftAP and preserves the runtime profile, station, schedules and
no-repeat watermark. A reboot before or during that window closes it without
automatic reopening; fresh physical/USB-local confirmation is required.
Provisioning reset produces those access-recovery end effects and also selects
an unprovisioned tombstone or a separately confirmed device-bound
build-bundle mode; it never falls through to legacy Wi-Fi/trust. Its durable
`reset_pending` transaction commits source mode before public-default activation
and clears intent before enrollment or SoftAP starts. Neither operation is the
full operational erase.
The core-0-owned onboard LED identifies a device and slow-blinks only while
SoftAP is actually ready. It is advisory and never proves RF or output safety.
These behaviors are production-wired through the access/reset/indicator core.
An associated Wi-Fi client retains every AP path. The final disconnect starts a ten-minute inactivity interval. An unjoined Console request retains its 120-second join grace; other initial windows last ten minutes. Browser sessions and button holds do not substitute for an association or reopen expired access.

## Time policy

The autonomous NTP implementation is [μChrony](../../src/microchrony/README.md),
an original MIT portable engine with a Pico network/clock adapter. Chrony 4.9
is an external private test reference; no Chrony code is linked into firmware.
The [UTC/RF contract](clock-discipline.md) defines compatibility and measurement
boundaries. Full Chrony behavioral equivalence is not established.

The Pico adapter checks the configured IPv4 endpoint and UDP port 123. The
engine correlates 48-byte basic NTPv3/v4 server replies with a one-shot random
origin token, validates ordered server timestamps and root metrics, unfolds the
NTP era, and rejects unsynchronized or denied sources. RATE requests back off;
other stratum-zero responses withdraw the association. These checks do not
authenticate the server or network. The application restricts imported UTC to
2025–2099. Pending leap indicators are exposed to the job policy; equivalent
Chrony leap execution has not been demonstrated.

Acquisition uses a bounded initial burst of four good replies in at most eight
attempts. A regression can establish an initial UTC epoch after three admitted
observations. Subsequent phase correction is slewed. Weighted regression,
identified delay asymmetry, residual runs, source agreement, root distance and
frequency uncertainty govern progressive confidence. There is no 32-sample,
30-minute, fixed half-window agreement or two-hour convergence requirement.
Repeated status reads and rejected samples never make an old fit fresh.

Configured pool names ending in `pool.ntp.org` use four distinct IPv4
associations through the corresponding `0`–`3` aliases. Duplicate endpoints are
not queried twice. Each source has at most 64 original accepted measurements.
Agreeing sources can be combined; contradictory minorities are rejected.
Other names and IPv4 literals use one association. DNS is asynchronous and
foreground-only. Responding admitted associations retain their endpoint;
loss, denial, excessive root distance or source rejection permits replacement.
A changed endpoint or link establishes a new source cohort. DNS never supplies
UTC or weakens job admission.

The Pico profile uses the Chrony settings equivalent to `minpoll 6 maxpoll 6`,
`maxdrift 100` and `maxclockerror 50`: normal polling is every 64 seconds plus
less than one second of jitter, the oscillator range is ±100 ppm, and holdover
retains its conservative 50 ppm allowance. The existing job limits remain
500 ms total uncertainty and 90 seconds since an actual source observation,
checked at admission and launch. Clock status can enter holdover through
180 seconds. Packet acceptance, statistical synchronization and permission to
launch a job are separate. Delay filtering or an outage can skip slots.

The single μChrony model supplies UTC frequency and finite phase slew directly;
there is no second NTP servo. Immutable clock copies include the end of a slew
and the subsequent frequency for local alarm conversion. Projection and inverse
mapping use checked integer arithmetic and charge microsecond quantization.
Source age remains tied to an original receive timestamp. Frequency confidence
is statistical and conditional on source/network behavior; it does not establish
independent absolute UTC or RF accuracy.

Routine status contains compact source, phase, frequency, skew and readiness
summaries. Complete original records use [bounded USB pages](ntp-usb-diagnostics.md).
Persistent manual PPM remains independent and is the only RF correction source.
NTP estimates and saved RF priors have no RF selection path. The
[UTC/RF contract](clock-discipline.md) defines retained journal compatibility.

The time arbiter accepts authenticated controller/phone time when SNTP is unavailable.
The device computes uncertainty from a fixed 250 ms phone allowance, the full
round trip and local margins; it retains the 500 ms uncertainty and 90-second
ARM-age gates, requests refresh no slower than 60 seconds and starts every reboot
unsynchronized. Phone time reports `leap=normal` as an explicit limitation.
The controller/SNTP arbiter and authenticated BLE/field HTTPS controller-time
adapters are production-wired. USB management has its separate qualified
[time exchange](../protocol/USB-Management.md#utc-exchange), independent of Pico
Wi-Fi. These observations supply UTC/slot timing, not RF oscillator calibration;
physical clock-accuracy claims remain bound to their recorded measurements.

## Scheduling, flash and failures

The scheduler considers a future occurrence only 2–10 seconds ahead. It never
catches up missed slots. A global persisted UTC watermark is reserved **before**
engine preparation; attempts that fail afterward are skipped, even across a
reboot. A backward UTC step cannot repeat any reserved or earlier occurrence.
Changing schedules or station identity does not reset the watermark. A large
erroneous forward clock step can therefore suspend scheduling until UTC catches
up or an operator deliberately resets storage; this favors no repeats over
availability. This is an at-most-once attempt policy, not guaranteed delivery.

A two-sector 8 KiB access journal occupies
`0x3f3000`–`0x3f4fff`, the project-owned BTstack bank occupies
`0x3f5000`–`0x3f6fff`, and the profile journal occupies
`0x3f7000`–`0x3fafff`. The four existing standalone sectors remain
at `0x3fb000`–`0x3fefff`, and E10 remains at
`0x3ff000`–`0x3fffff`. Saved progress occupies `0x3f0000`–`0x3f1fff`,
with diagnostic scratch at `0x3f2000`–`0x3f2fff`. Linked application FLASH ends at
`0x3ee000`; a separate NTP-learning journal occupies `0x3ee000`–`0x3effff`.
Maintained application linker layouts and image checks reject
ordinary image content in all reserved regions. Station, schedules and watermark
addresses are unchanged.

Manual PPM and learned UTC rate use separate journals. Manual correction remains
unchanged until an explicit configuration change or operational reset. The
legacy NTP RF-mode flag remains readable but is inert. The learned cache binds
device, algorithm/topology version,
normal clock ratio, source endpoint, boot, epoch and original reference time.
UTC frequency/skew retains its original source provenance.
Writes require idle/unowned state outside provisioning, reset and reboot, a
minimum five-minute interval and a meaningful 0.1 ppm change or a halving of UTC
skew. Pending UTC learning survives that cooldown in RAM. Production does not
stage new RF priors.

The 192-byte cache payload version 2 stores pure UTC frequency and skew,
separately from temporary phase-slew rate and any RF prior. It reads version 1
with broad unknown skew; older images do not understand version 2. After restart,
a saved frequency seeds μChrony with a broad provisional error bound. It restores
no UTC, sample history or freshness; acquisition still requires real replies.
Legacy RF payloads remain readable to preserve journal compatibility, but cannot
supply a startup fallback or any other RF correction. They do not invalidate the
separate UTC seed.
Cache corruption cannot make configuration unhealthy. A torn cache update can
recover the last verified record; unknown device/version/topology records are
rejected without erasing them. Full operational reset erases and verifies both
cache sectors; provisioning-only reset preserves them.

Current firmware updates preserve the final 72 KiB. Historical images with a
higher application boundary can overwrite the learned cache during downgrade;
verification of their original layout does not establish cache preservation.

The access journal holds password state, access epoch, authorized stable bond
identities, field mode and durable reset intent. Source mode/tombstones remain
inside the profile transaction. Erased access storage requires a separately
authorized confirmation path; corrupt or pending state fails closed.

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
armed/running jobs. Flash accesses use the SDK's safe routines with interrupts
masked; the physical image additionally coordinates its RF worker through SDK
multicore lockout; core 1 retains physical RF/peripheral ownership.

CRC32 detects torn writes and accidental corruption; it is not a security MAC.
A non-erased invalid record in **either** journal latches a storage fault. The
firmware does not silently restore an older enabled configuration or ambiguous
watermark. Torn writes can therefore require operator recovery. The current
remedy for these standalone-journal faults is separately authorized
**full-device/BOOTSEL flash recovery**: erase the device flash, reflash and
reprovision. That manual path clears credentials and no-repeat history; it is
not the implemented **full operational erase**, which
uses a durable `reset_pending` transaction and leaves E10 under its existing
recovery contract. Both are distinct from access recovery and provisioning reset,
which preserve station, schedules and watermark. A normal UF2 update preserves
the reserved region. Do not erase storage as an automatic response to a CRC
error. Future storage-schema changes require an explicit migration design, not
reinterpretation of old records.

At the maximum two-minute schedule, watermark storage programs 720 pages/day,
with about 45 sector erases/day shared between the two banks. This is 16
reservations per erase, rather than one erase per job. Flash endurance and
brownout behavior need device-specific qualification; no lifetime claim is made.
Configuration writes are administrative, not performed on each network sample.

The current physical image services RF on core 1; core 0 owns authority and
transports. Consumer profiles and active TLS or Plain LAN listeners keep Wi-Fi
polled through Armed/Running. The earlier deferral remains only for non-consumer
operation without either listener. The accepted clock observation ages locally and USB WTP
remains serviced, including ABORT. BTstack, SoftAP and controller-time adapters
remain on core 0; the shared IndicatorController owns the boot-selected onboard
or external LED. These source ownership rules do not establish physical RF coexistence,
mode/band/clock qualification or release reliability. Selected work is maintained
in the [consolidated backlog](consolidated-backlog.md).

## Validation

Use the [development checks](README.md#deterministic-validation) with an unused
build directory and installed pinned dependencies. Existing standalone, journal,
clock, frequency-policy and WSPR-plan tests exercise corruption/interruption,
rotation, repeated/backward slots, competing ownership, failed reservation and
preparation, time loss/uncertainty and complete local job behavior. Simulation
and cross-linking establish neither device timing nor conducted RF performance.
