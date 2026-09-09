# Phase 11.4 D3 execution and adversarial review

D3 is **PASS for the bounded inhibited-device cases below**. Two authorized
Bohica-IoT outages produced USB-observed Wi-Fi loss while Wi-Fi remained enabled.
Native Mac records expired, Linux returned completed negative lookups, and the
Pico recovered automatically with its original boot and certified name. During
the second outage, an already-running finite job completed locally with output
inhibited. This does not close intermittent connectivity, Chrome recovery,
new-address DHCP, overnight memory stability or RF qualification.

The [execution prompt](phase11-4-d3-prompt.md) was executed on 2026-09-09 from
clean Pico devel `36180a24dbe5042a23644646a50051df23066982`. The
[Orbi research](phase11-4-d3-orbi-research.md) informed the selected fault.
Private logs, captures, helpers and generated executables are under
`build/phase11-4-d3/`, bound by the [hash index](phase11-4-d3-evidence.json).
Only tests and documentation changed; no runtime, firmware, SDK, protocol or
independent WsprryPi source was changed.

## Identity and authority

Target: sole Pico 2 W / RP2350 on wspr5; USB serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, hostname
`wsprrypico-0a60df.local:18443`. INFO and USB HELLO/CAPS/STATUS confirmed revision
`5ee5bcf93c56-dirty`, matching deployment identity and standard
`inhibited-standalone-simulator` engine. Boot stayed
`cebcd4720cd9919a7cfaff492b717a85`; storage stayed healthy and schedules disabled.
The recorded deployment hashes are historical deployment identities, not a new
flash readback:

- UF2: `2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4`
- ELF: `f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65`
- Server certificate: `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`
- Existing CA: `2ef7ec890d48e9283286ee09c6b549756f3d3cff530e5cb030ced6ae4c40442b`

The user explicitly authorized all tests, then a brief Bohica-IoT outage. Both
management hosts were wireless: Mac `.27`/en0 and wspr5 `.117`/wlan1 on Bohica;
Pico `.47` on Bohica-IoT. After being told both paths could disappear, the user
explicitly accepted Wi-Fi-only management. Detached wspr5 USB/packet/resolver
recorders fsynced local logs; native Mac dns-sd observations ran separately.
Network operations used the unsandboxed execution path. No router-wide debug
capture, router reset, other SSID setting, trust import, flash, GPIO or RF action
was performed. The installed service was not paused or modified.

## Physical observations

Orbi RBR850/RBS850 firmware `V7.2.8.2_5.1.18` provided the IoT enable control.
The user assisted with authenticated Apply and restoration. A checked, unsaved
form was not accepted as proof that the network was enabled. Restoration took
longer than intended; recorder evidence and the user's correction are retained.
No Console WIFI OFF/ON or Pico restart was used to recover either case.

| Case | Authoritative observations (UTC) | Result |
| --- | --- | --- |
| First outage, recorder `174954Z` | Link loss 17:54:09.175622; link recovered 17:57:50.553332, about 221.4 seconds later; same boot and `.47` | Cache-loss/recovery case passes. The first 100-second job had already completed before confirmed link loss, so this attempt does **not** prove active-job continuity. |
| Active outage, recorder `180106Z` | Link loss 18:04:08.078254 with the second job Running; terminal completion recorded 18:04:23.488319 while link remained down | Finite-job continuity passes; one LOAD and ARM, no replacement submission. |
| Second restoration, recorder `181019Z` | Still down at 18:08:38.116052 when the first recorder ended; recovered by 18:10:19.727395 when the next recorder began | Same boot/device/name/address, active mDNS, synchronized clock and verified HTTPS. Recovery occurred within this observation gap; its exact transition time and probe sequence were not captured. |

At loss, link_status was `-2`, IPv4 and advertised name were empty, mDNS was
`waiting_address`, Wi-Fi enabled and requested_enabled null. USB remained
responsive. In the active case the job was
`8ec73ebd2ac54ab8859286cd690c1b1b`, owner
`e790839dbb1a4ad38f5cb280c6758615`. The actual TLS WTP client admitted a complete
110-second tone at 3,570,110 Hz using CAPS and synchronized GET_CLOCK with a
10-second start lead. USB independently confirmed identical job/owner/boot while
Running through loss. The 60-second lease expired during execution, persisted
through Running, then released at Complete according to the WTP contract. The
terminal record remained retained. Output was explicitly false throughout the
USB observations; this was inhibited scheduling evidence, not transmitted RF.
The client was the recorded Python TLS driver, not a new production-client test.

## Cache and packet evidence

The two Linux captures contain 149 and 133 packets, respectively, with matching
tcpdump counts and zero kernel drops. Pico-origin native A answers had source
MAC `88:a2:9e:0a:60:df`, address `.47`, IP TTL 255, cache-flush and record TTL 120.
No Pico-origin TTL-zero record was captured in either bounded capture; goodbye
attempts remained 6 and failures 0. This is receiver evidence, not proof that
no frame could have existed elsewhere on the mesh. Ephemeral-port legacy-unicast
answers used TTL 10 and were excluded from native-cache expiry calculations.

| Observation | First outage | Active outage |
| --- | --- | --- |
| Last captured native positive A | 17:52:04.882973 | 18:02:56.590429 |
| Native Mac removal | 17:54:27.690277 | 18:04:57.386331 |
| Removal after captured A's nominal expiry | 22.807 seconds | 0.796 seconds |
| Native Mac return | 17:57:54.738 in the same observer | Positive Add at 18:10:24.399 in the restarted observer |

These are descriptive cross-host timestamp differences, not precise cache
implementation timing. The Linux capture is not a complete view of packets
received by the Mac; no subsecond clock-alignment bound was established. The
first 22.8-second difference remains unexplained, and no exact 120-second cache
conformance claim is made. Native removal was observed without cache flushing
or synthetic removal. Linux completed negative lookups with exit 2, separately
from timeouts, then returned `.47` after each recovery. First-case packet evidence
also includes the returning positive cache-flush A announcement.

## Cleanup and limitations

The user restored IoT enabled with the UI's default of both bands. Cleanup
returned it to the original **2.4 GHz only**, same Bohica-IoT name and WPA2 mode,
and verified the completed Apply. This additional band restoration is cleanup,
not a third instrumented D3 case. Credentials were preserved. No reservation or
access-control policy was created in D3.

After saving both terminal records, authenticated CLAIM/RELEASE retired only the
completed current job. Final USB HELLO/CAPS/STATUS and Linux HTTPS proved empty,
inactive, unowned state with both terminal records retained. Mac native
resolution and authenticated HTTPS passed. Actual Chrome reload still returned
`ERR_BLOCKED_BY_CLIENT`; this failure remains open. The recorded AA0NT/EM18,
power 20, disabled schedule, expiry and watermark were preserved. Final host
inspection confirmed active wsprrypi.service, RP1 output disabled and unchanged
installed binary/configuration hashes from D1. D3 recorders, controllers, native
observers and captures were stopped; the remote process check found none.

Resource samples had no lwIP or TLS allocation errors and remained within their
reported capacities. The active loss returned lwIP heap/PCB/segment/pool usage to
zero. These brief observations do not establish absence of a slow leak or explain
the reported morning web unresponsiveness. Main-network access was available for
sampled management operations; continuous loss-free service for every household
client was not measured.

## Adversarial review and validation

Review strengthened portable mDNS tests for stale addresses after link loss,
late callbacks, a 150-second host outage, automatic same-name reprobe and loss
during probing. Pinned lwIP tests now assert no packets/goodbye after link-down
removal, restored heap/timer usage and no residual work after 150 seconds before
the existing repeated recovery tests. No runtime defect was found in this slice.

Four compiled mutations were rejected: ignoring unusable link, sending goodbye
after loss, accepting late callbacks and retaining registration. An initial
mutation compilation failed because of an unused parameter; it was retained and
not credited as behavioral rejection. The generator was corrected and both
subsequent assessments rejected all four at runtime.

Physical review retained the first job's non-overlap, corrected the premature
restoration assumption, restored the original band, and explicitly limited the
second recovery timing and cross-host TTL claims. The first offline audit rejected
14 altered-evidence cases. Reassessment added capture-count agreement, final
router/host state and second Linux recovery, then rejected 19 cases: wrong boot,
unknown output, orderly disable, false loss, wrong owner, terminal reordering,
duplicate submission, wrong USB reply, capture loss/count/origin, missing cache
removal, timeout presented as negative, wrong certificate, missing terminal,
stopped service, changed band, missing recovery and a captured goodbye.
The final assessment passed with those recorded limitations; no actionable
finding remains within this bounded D3 slice.

Affected checks passed: both mDNS CTest suites; four compiled mutation refusals
repeated; clang-format; WTP validation (23 schema, seven raw-JSON, one framing,
eight transition cases); physical evidence reassessment; documentation links,
private artifact hashes and diff whitespace. Host checks do not qualify physical
RF, overnight resources or another mesh topology.

## Remaining Phase 11.4 work

| Item | Still required |
| --- | --- |
| D1 | Actual DHCP address reassignment and same-name Mac/Linux/Chrome/production recovery; prior router LAN Apply returned HTTP 400 |
| B2 / D2 reliability | Explain intermittent resolver/ARP/TCP recovery, reproduce reliably and resolve Chrome blocking; D3 does not erase prior failures |
| E1 | Second physical Pico for independent names/device identities and per-board trust rejection |
| Startup / overnight stability | Sustained connectivity and memory observations addressing reported web unresponsiveness |

Phases 11.5 resource/contention, 11.6 conducted RF and 11.7 joint closure remain
separate.
