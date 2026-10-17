# P15.20 handoff: GPIO drive strength

Add this operator behavior to the Pico and selected-Pico Pi hardware pages:

- GPIO drive strength offers 2 mA, **4 mA (default)**, 8 mA and 12 mA.
- This is nominal electrical drive on the selected direct RF output GPIO.
  Actual RF power depends on load and frequency. It does not adjust reported
  WSPR power, calibrate output, or qualify another band or mode.
- Read the selected member's drive. Unsupported or unreachable firmware has no
  observed default. Saved, boot selection and verified physical pad are distinct.
- Select a value, Save GPIO drive, then use the existing explicit Pico restart
  workflow. A changed hardware setting keeps output inhibited for that boot;
  returning to the boot value does not clear an already latched restart.
- Selection/preview never writes or transmits. Conflict, session loss or lost
  replies preserve the draft. Read and review authoritative saved state before
  a new explicit action; a saved write can survive a lost acknowledgement.
- A draft belongs to its original member and boot. Explicitly discard it before
  applying a draft to another observed member. Other Pi backend controls retain
  their own units and defaults.
- USB management does not require Pico Wi-Fi. Network management uses its
  existing authenticated Consumer-Radio or engineering connection; plain WTP
  job transport grants no configuration authority.
- Older ordinary saves preserve omitted drive. Deliberate complete replacement,
  Console CONFIG and full reset default omitted drive to 4 mA. Wi-Fi-only reset
  preserves it. Unsupported firmware downgrade after a nondefault Config/new
  progress record is not a supported rollback path.
- Saved progress can store drive without station completeness. It does not
  apply hardware. Explicit domain `drive` applies the saved drive; radio/all
  application preserves a later drive selection.

Use the final [execution record](phase15-15-results.md) for validated source,
visual artifacts and physical limitations. Keep implementation/test narration
out of operator pages. Refresh screenshots from the final served interface;
visual fixtures are software evidence, not photographs of physical readback.
The separate documentation repository and publication remain outside P15.15.
