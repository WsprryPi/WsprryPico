# Pin allocation feature

The [selected contract](../pin-assignment-contract.md) defines hardware
eligibility. This implementation adds pin-plan validation and boot-applied
assignments for direct PIO RF, active-low switch input and the shared indicator.
Amplifier/LPF execution adapters remain unavailable; Si5351 is deliberately
unavailable in this feature. Their candidate allocations can be reviewed but
cannot be saved as operational configurations. These checks do not qualify RF
performance on newly selected pins.

## Management API

Existing member authentication and Host/Origin/content-type checks apply.

- `GET /api/v1/pins`: `{choices, active}`. Choices include eligible GP numbers,
  indicator selections, adapter support and fixed pairs with stable IDs 0–11
  in the contract table order. Active is the boot-applied plan.
- `POST /api/v1/pins/validate`: review the complete candidate below. No persistence,
  revision change, GPIO access or engine change occurs. It returns `valid`,
  `error`, `role`, `owner`, `gp`, partial ownership information, pair availability,
  `operational_supported` and `applied:false`. Malformed schema returns HTTP 400;
  a well-formed conflicting plan returns HTTP 200 with `valid:false`.
- `PUT /api/v1/config`: the existing full configuration accepts optional `pins`.
  This mutation requires If-Match and idle/unowned/nonfaulted state. Conflicts
  return HTTP 400 with role/owner/pin information. Eligible but unimplemented
  adapters return `unsupported_pin_adapter`. Other invalid configuration remains
  `invalid_config`. Failed validation preserves the old journal and revision.

A complete pin plan uses Pico GP numbers, JSON null for unallocated resources,
and one pair ID instead of independent SDA/SCL fields:

```json
{
  "engine": "direct",
  "rf_gp": 2,
  "i2c_pair": null,
  "button_gp": 14,
  "amplifier_gp": null,
  "lpf_gps": [],
  "indicator": "onboard_led",
  "indicator_gp": null,
  "indicator_active_high": true
}
```

`indicator_active_high` is optional and defaults to true; it applies to external
indicators. All other plan members are required. `indicator` accepts
`onboard_led`, `external` or `disabled`. Direct mode requires one `rf_gp` and
null `i2c_pair`; I²C mode requires null `rf_gp` and one pair ID. Plans are bounded
at 2,048 bytes and 26 selectors. Operational Config retains its 1,800-byte limit.
No independently allocated auxiliary I²C bus is supported.

The current input adapter supports active-low/pull-up operation only. Its pin is
configurable, but its reset/stop/setup gesture and debounce policy are preserved.
Builds with the runtime-button feature disabled do not instantiate that adapter.

## Persistence, activation and recovery

Legacy configuration without pins retains GP2 RF, GP14 switch and onboard LED.
Default pin plans keep the legacy canonical serialized configuration. Nondefault
plans append the pin object; older firmware rejects that extension, so downgrade
requires restoring default assignments before loading an older image.

Pin settings take effect only after reboot. Saving a changed pin plan latches
JobService RF admission inhibited for the rest of the boot. Autonomous scheduling
also stops pending restart. A later station edit, or restoring the original pins,
cannot clear the latch. `GET /api/v1/config` reports saved settings while
`GET /api/v1/pins` reports active settings. No second RF authority is introduced.

Store reload rejects invalid or unsupported pin data even with a valid journal
CRC. An unhealthy Store boot inhibits the RF worker; it must not generate RF on
a default fallback pin. Recovery remains through the existing recovery paths.

The indicator's one controller uses the selected external GPIO exclusively for
TX, with Identify/SoftAP cues remaining on the onboard LED. Without an external
selection, TX holds the onboard LED solid ahead of those cues. Disabled selection
suppresses indication. The P13.1 launch handshake checks the selected TX output
before activation; an onboard AP flash cannot acknowledge an external TX write.
Field-GATT keeps its existing cue-pattern vocabulary; that pattern describes the
provisioning cue rather than an independent RF measurement. External active-low
and active-high outputs preload the requested level before enabling direction.

## Reproduction

In a clean Linux source snapshot with CMake 3.24+ and a C++20 compiler:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel 2
ctest --test-dir build-host --output-on-failure
node tests/network_browser_tests.js
```

Git-history acceptance checks require the existing repository history. Recovery
web checks require the project's pinned bootstrap-web dependencies. A source-only
snapshot without those prerequisites cannot reproduce those checks; run them in
the repository with existing dependencies instead. Never infer physical pin,
button timing, RF-chain or Phase 12 acceptance from these host checks.

See the [execution prompt](pin-allocation-execution-prompt.md) and
[review/results](pin-allocation-review.md) for the exact validation disposition.
