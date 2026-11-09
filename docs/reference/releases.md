# Release notes

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
