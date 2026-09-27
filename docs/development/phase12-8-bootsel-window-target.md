# P12.8 core-1 BOOTSEL target diagnostic

Status: **PHYSICAL PRESS/RELEASE SAFETY OBSERVED; CONSUMER CLAIM NOT IMPLEMENTED**
(2026-09-27). This is one RF-inhibited Candidate A diagnostic, not a P12.8 or
Phase 12 closure result.

## Admission and setup

- Operator authorized this exact flash and one released/button window, then
  authorized one retry after the first prompted window received no press.
- Candidate A: Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`. Candidate B was untouched.
- Host: `wspr5`, boot `ffe09284-0e6b-41ee-9fe7-092867f72107`; isolated
  `wlan2` joined BSSID `88:a2:9e:0a:60:df` on the open
  `WsprryPico-0a60df` AP. Ethernet remained the management route.
- The approved RF-inhibited diagnostic UF2 SHA-256 was
  `03611155a0f7302d5fe4ad069e6a2c18d8872dcd2dc1fd7a0a541400ab428c66`.
  It was verified on `wspr5`, loaded and verified by `picotool` against that
  exact USB serial, and left installed. `INFO` read back source revision
  `3f56f5e1aaa9` and the expected device ID.
- Before flashing, `STATUS` was Empty with inactive output and
  `inhibited-standalone-simulator` engine; `INFO` reported healthy
  network-only generation 1. The diagnostic kept that generation.

## Observations

| Run | BOOTSEL result | Continuity |
| --- | --- | --- |
| Released button | `ok=true`, no press, `elapsed_us=5000091`, `result=0` | Same boot ID before/after; core-1 flash-read counter advanced; HTTP 200 before/after. AP GETs timed out during the expected five-second flash-safe pause. |
| First prompted window | `ok=true`, no press, `elapsed_us=5000090`, `result=0` | Operator confirmed they did not press. This is a non-qualifying timing attempt, not a device fault. |
| Authorized retry with physical press/release | `ok=true`, `duration_ms=702`, `elapsed_us=5241140`, `result=0`; installed image returned `valid_press=false` only because its 600 ms design cutoff rejected the human press. | Same boot ID `d8e0c3c424b19726ee81d7de42e338c5`; core-1 flash-read counter advanced; no fault or output; AP GETs timed out during the pause and returned HTTP 200 afterward. |

The physical press and release was observed with core 1 continuously reading
flash before and after the safe zone. The device did not reset or enter a
fault state. `INFO` after the retry reported fault stage/status zero,
network-only generation 1 and a valid core-0 stack guard. `STATUS` remained
Empty with `output_active=false`, the inhibited engine and healthy storage;
`STORAGE` and `ACCESS STATUS` remained healthy. No station credential, owner,
job or RF action was used.

The 600 ms cutoff was a consumer-design error: an operator must only press and
release, with no timed hold. Source after this installed diagnostic now
accepts a debounced press/release within the prompted window, and the portable
claim slot uses an internal 20 ms bounce guard and 10-second stuck-hold bound.
The **installed image still has the old cutoff**; no new target gesture-validity
claim is made from the source change. This run does establish physical
core-1/flash/BOOTSEL press-release survival and AP recovery for the exact
diagnostic setup. A Safari prompt and owner transaction remain unimplemented.

## Fixture and remaining gates

The temporary `wspr5` NetworkManager `phase12-bootsel-ap` profile was
disconnected and deleted. `eth0` remained connected for management, `wlan1`
remained on its prior station network, and `wlan0`/`wlan2` were disconnected.
Candidate A retains the newer RF-inhibited diagnostic; no rollback was done.

P12.8 still requires Owner-HTTP/1 route and crypto integration, generated
device trust, atomic activation and a Safari prompt delivered before a bounded
safe zone. P12.9–P12.12 require their own browser, phone, ownership/recovery
and Stage A evidence. This diagnostic is not an owner claim or RF acceptance.
