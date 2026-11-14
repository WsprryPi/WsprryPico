# Release notes

## 1.0.0-rc.3

RC.3 adds gray-line scheduling and improves setup, recovery, and USB installation on Pico 2 W.

- Morning and evening gray-line periods have independent solar-elevation windows and optional WSPR dial or Morse-message frequency overrides. Existing schedules determine when transmissions are due. Calculations use the selected saved locator or a fresh GPS position; unavailable time or location holds the occurrence.
- Daylight and night beacon schedules can use the saved station locator without GPS, with usable UTC.
- Initial Wi-Fi setup includes hostname editing.
- Recovery navigation is available from the AP interface and authenticated Advanced Wi-Fi controls, with contextual help. The firmware-preserving settings reset is labelled **User wipe**.
- Scheduling controls and the presentation of unset calibration and gray-line settings are clearer.
- USB installation provides clearer picotool diagnostics and Linux permission handling, including optional sudo limited to picotool operations. Installation instructions clarify BOOTSEL, native Windows UF2 use, and USB troubleshooting.
- AP unlocking allows the normal request deadline when establishing browser time, and the HTTP server releases acknowledged responses promptly so following requests can connect. HTTP connection diagnostics are available through the USB console.
- Locked and unlocked controls use equally bold red and green borders. Successful unlocking clears button focus; keyboard navigation retains its visible focus indicator.

The linked release build records the canonical software checks and firmware reproducibility result. Production Pi/Pico network and USB integration checks passed for the AP unlock changes. Development firmware was installed and preserving upgrades were verified on Pico C. Physical installation, iPhone automatic Wi-Fi sign-in, timing, and RF qualification of this exact published release image remain unverified. Si5351 automatic correction remains experimental.

I²C LPF output control remains planning only and is not included in RC.3. See [scheduling configuration](../configure.md#gray-line-scheduling), [maintenance and recovery](../maintain.md), and [installation and preserving upgrades](../install.md).

## 1.0.0-rc.2

RC.2 improves preparation of long transmission jobs, indicator scheduling, configuration validation, and GPS correction diagnostics on Pico 2 W.

The canonical build, software tests, and production Pi/Pico network and USB integration checks passed. Physical installation and RF qualification of this exact image were not performed. The conducted campaign remains incomplete.

- Long job sequences use bounded memory during loading. Accepted jobs still execute locally on the Pico.
- Indicator timer programming can recover from a missed programming opportunity within the accepted UTC start window. The job keeps its original start deadline and complete transmission sequence.
- Configuration merge updates and hostname status use consistent current schemas across Pico and its controllers.
- Automatic correction diagnostics retain the input selected for the accepted job, even when the live GPS estimate advances. Qualification checks can verify the actual selected correction without depending on the timing of a later GPS read.

The available transmission modes are WSPR, finite test tone, QRSS, FSKCW, and DFCW. The supported outputs are direct GP2 through the RP2350 PIO/DMA engine and the documented Si5351 hardware profile. See [RF connections and limits](output.md) and [time and correction](time.md).

Si5351 automatic correction remains experimental. The tested Si5351 was already close to the correct frequency; the measurements did not establish a consistent improvement from automatic correction. Measure the carrier before and after enabling it. If it does not help, leave it off or use a measured manual adjustment. This result does not qualify other reference modules, output power, or emissions.

Use the [installation and preserving-upgrade instructions](../install.md) to select an exact published firmware version. The semantic release and the moving development download are separate selections.
