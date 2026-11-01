# Support and bug reports

For help with WsprryPico, first check [Troubleshoot](troubleshoot.md). For installation or recovery problems, see [Install firmware](install.md) and [Maintain and recover](maintain.md).

## Ask for help

Search the [existing issues](https://github.com/WsprryPi/WsprryPico/issues) for the same problem. If none matches, [open an issue](https://github.com/WsprryPi/WsprryPico/issues/new) and describe what you need help with. A GitHub account is required to post. If an existing issue matches, add any new details there.

For a problem in the WsprryPi controller, use the [WsprryPi issue tracker](https://github.com/WsprryPi/WsprryPi/issues). If you are unsure which project is responsible, describe how the Pi and Pico are connected and which controls you used.

## Report a bug

Describe the smallest set of steps that shows the problem. Include exact error wording and distinguish what you expected from what happened. You can copy this checklist into your issue:

```text
Summary:
Firmware version and channel (or source revision for a custom build):
Board model:
Connection (home Wi-Fi, Pico setup/field Wi-Fi, or USB):
Standalone or WsprryPi-controlled (include WsprryPi version if used):
Browser and operating system, including versions:

Steps to reproduce:
1.
2.
3.

Expected result:
Actual result and exact error message:
How often it happens:
Relevant status, logs, or screenshots:
Checks or recovery steps already tried:
```

## Find the information for your report

Include what you can obtain. If a page or connection is unavailable, say so and report the details you already have.

| Information | Where to find it |
| --- | --- |
| Firmware version and source revision | Follow [Open the Console in a browser](usb.md#open-the-console-in-a-browser), or [use a terminal on macOS or Linux](usb.md#find-and-open-the-console-on-macos-or-linux). Send `INFO` and copy `firmware` and `revision` from the [diagnostic reply](usb.md#read-the-address-and-web-service-status). The installer's final result also records the installed version and revision; see [Preserve settings during an update](install.md#preserve-settings-during-an-update). State whether you installed a Beta release, published devel firmware, or a custom build. |
| Pico identity | Open **About this Pico / Diagnostics** and copy the full stable device ID and observed boot ID; see [Support information](maintain.md#support-information). If the browser is unavailable, `INFO` supplies `device_id` over [USB Console](usb.md#read-the-address-and-web-service-status). |
| Board model and RF connections | Check the board's printed model and describe your wiring, filtering, amplifier, and load, if used. Compare with [Hardware connections](start.md#hardware-connections). |
| Connection and control method | State whether you joined home Wi-Fi, the Pico's own Wi-Fi, or connected over USB. See [Connect to your Pico](connect.md) and [Use with WsprryPi](wsprrypi.md) to identify the route. Say whether the Pico's browser/saved schedule or WsprryPi was controlling the transmission. If WsprryPi was used, include its version. |
| Browser and operating system | Copy the browser's version from its **About** page in its menu or settings. Copy the operating system's name and version from **About This Mac** on macOS, **Settings → System → About** on Windows, or your Linux distribution's **About** panel. |
| Mode, frequency, job state, and RF output | Choose **Transmitter status → Refresh** and copy the relevant fields, including frequency units. [Status, stop, and connection loss](operate.md#status-stop-and-connection-loss) explains each field. |
| Clock state and uncertainty | Copy **Clock** from the refreshed transmitter status, including the uncertainty after `±`. See [Read the clock status](reference/time.md#read-the-clock-status). |
| Browser access failure | Copy the exact URL from the address bar and the complete error text. Follow [Pico answers ping but the browser cannot open its page](troubleshoot.md#pico-answers-ping-but-the-browser-cannot-open-its-page) and report which checks worked or failed. [USB diagnostics](usb.md#read-the-address-and-web-service-status) explains how to read the current IP, hostname, and web-service readiness. |
| Diagnostic logs | Follow [USB diagnostic logging](usb.md#usb-diagnostic-logging) to collect Pico logs through WsprryPi, or [UDP diagnostic logging](udp.md) for a network collector. Include the time of the problem and the relevant surrounding records. Logging must be enabled before it can capture an event; if no logs were collected, say so. |

Copy exact errors or attach a screenshot that includes the relevant control and message. List the troubleshooting or recovery steps you already tried and their results.

Remove passwords, private keys, tokens, and other private information before posting logs or screenshots. Keep installer backups and credential-bearing files private. Report what you already observed; reproducing a bug does not require transmitting or erasing settings.

## Report a security problem

Follow the [security reporting instructions](https://github.com/WsprryPi/WsprryPico/blob/devel/SECURITY.md). Report suspected vulnerabilities privately to the maintainer; request a private contact channel without posting exploit details publicly.
