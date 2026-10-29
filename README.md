# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W**, with its RP2350 processor, into a radio beacon. It can run **standalone**, using settings saved on the Pico and its own browser controls, or accept transmissions from **WsprryPi**, a controller running on a Raspberry Pi.

**WSPR**, Weak Signal Propagation Reporter, sends digital beacon messages containing station information. The slow Morse modes use different signaling: **QRSS** switches the radio signal on and off, **FSKCW** shifts to a lower frequency during gaps within a message, and **DFCW** uses different frequencies for equal-length dots and dashes. Controllers and prepared job files can also submit a **finite test tone**, a steady signal with a specified duration. See the [operator manual](https://wsprrypico.readthedocs.io/en/devel/) for the modes and controls.

A **job** is one complete transmission, including any message repeats and gaps. A **schedule** starts WSPR jobs or a saved QRSS, FSKCW or DFCW message automatically at selected UTC times. The Pico runs accepted jobs locally, so their timing does not depend on continuous USB or Wi-Fi delivery.

## What you need

- A **Pico 2 W**, a USB **data** cable and a reliable USB power supply. The original Pico, Pico W and non-wireless Pico 2 are unsupported.
- For the [USB firmware installer](docs/install.md), a **Mac or native Linux computer**, Python **3.10 or newer**, and `curl`. Firmware is the application stored on the Pico. Windows, Git Bash and WSL are unsupported by the installer; Windows users can use the [Chrome USB Console](docs/usb.md#open-the-console-in-a-browser) once firmware is installed.
- For standalone browser control, a compatible password-protected personal **2.4 GHz Wi-Fi network** and a current desktop or mobile browser with JavaScript enabled. Enterprise and WPA3-only setup are unavailable. The Pico serves the control page itself. The WsprryPi USB route below works without configuring Pico Wi-Fi.

**RF** means radio-frequency output. The Pico generates it on a **GPIO**, a general-purpose input/output pin. The factory hardware assignments are:

| Connection | Factory default |
| --- | --- |
| RF output | **GP2**, physical header pin **4** |
| Transmit indicator | **Onboard LED**; no external LED needed |
| Optional external control button | A normally open momentary push button between **GP14**, physical pin **19**, and **GND** (ground) |

External GPIO assignments can use **GP0–GP22** or **GP26–GP28**. Each GPIO can serve only one role; the settings prevent overlapping assignments. Settings use GPIO numbers, which differ from physical header pin numbers. Saved custom assignments take precedence over the defaults. The [hardware preparation guide](docs/start.md#hardware-connections) covers RF wiring, an optional external LED with its series resistor, and the external button. That button provides reset, transmission shutdown and setup Wi-Fi controls; the onboard **BOOTSEL** button is used for firmware installation.

## Standalone setup

1. [Prepare your Pico](docs/start.md). With power disconnected, check the pin assignments and connect an RF path with filtering, attenuation and a suitable load. Add an external LED or button if wanted.
2. [Install firmware](docs/install.md) over USB. Follow the first-installation procedure for a new Pico, or the settings-preserving update procedure for an existing WsprryPico.
3. [Set up Wi-Fi](docs/connect.md#first-wi-fi-connection). A Pico without saved Wi-Fi starts an **open** setup network named **WsprryPico-** followed by six characters. Join it without a Wi-Fi join password, open **http://192.168.4.1/** and save your home-network details. Keep the suggested time server unless a different one is needed, and wait for the saved-and-connected confirmation.
4. [Open the control page](docs/connect.md#open-the-control-page). Reconnect your phone or computer to the home network and use the Pico's current router-listed IP address or reported `.local` hostname, starting with **http://**. The default **Pico password** is the home Wi-Fi password saved during setup. A [separate Pico password](docs/maintain.md#change-the-pico-password) can be set without changing Wi-Fi. Select the lock beside the hostname to open the Pico password dialog and unlock controls. Use the header to select **Station Control** or **Wi-Fi/Host**; either view opens at the top. Station Control starts with transmitter status. Saved settings and detailed observations load while locked; open a section heading to inspect them. **Top** closes the settings sections and returns to the hostname, preserving drafts. Station details and clock synchronization are not needed to open the page or sign in.
5. [Configure your station](docs/configure.md). For automatic WSPR, enter your callsign, grid locator (the Maidenhead code for your transmitting location), reported power, whole-Hz WSPR USB dial frequency and schedule. Save valid station fields and explicitly apply the saved station before choosing **Save frequency**; a complete saved draft alone does not enable that control. A new installation has no selected dial frequency. Standalone WSPR centers its four tones 1,500 Hz above the dial, without random placement: `14095600` gives center `14097100 Hz`. Enter frequencies in **Hz** (hertz); **1 MHz = 1,000,000 Hz**. Keep schedules disabled while reviewing the settings. A saved **draft** is work in progress; **applied** settings are the configuration accepted for operation. Pin changes also require an explicit restart.
6. Follow [Your first WSPR transmission](docs/operate.md#your-first-wspr-transmission). When ready, save and apply **Enable standalone schedules** for automatic WSPR, or use **Send a message** for an individual or recurring QRSS, FSKCW or DFCW transmission. Review the reported clock, output and control status before starting.

If the Pico answers ping but its page will not open, follow the [browser troubleshooting steps](docs/troubleshoot.md#pico-answers-ping-but-the-browser-cannot-open-its-page). The [USB Console walkthrough](docs/usb.md) explains how to read its address and request setup Wi-Fi without an external button. A USB cable alone does not create a network connection or open the control page.

## Use with WsprryPi

Start with [Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html). In WsprryPi's **Setup → Fleet**, the **Fleet** list identifies available transmitters. Select the Pico for the Pi's jobs or assign it an independent output schedule. USB provides settings, controller time and transmission jobs without Pico Wi-Fi; supported network connections are another option. That manual covers Pi connections, schedules and Pi-managed firmware updates.

One USB cable provides separate Console, WTP, Management and Logging serial ports. Console remains available for interactive commands while WsprryPi collects diagnostic logs through Logging. Earlier firmware without the dedicated Logging port must be updated before collection can start.

Before switching to a Pi-run schedule, disable, save and apply the Pico's WSPR schedule, pause any saved message schedule, then confirm inactive output and released control. The two schedules are separate; stopping one does not disable the other. See [Use with WsprryPi](docs/wsprrypi.md) for the handoff in either direction.

## Transmission and timing

The RF output is **unfiltered** and needs filtering, attenuation, a suitable load and any amplifier appropriate for the chosen frequency and signal level. **Reported WSPR power** is the power value sent in the beacon message, expressed in **dBm** (decibels relative to one milliwatt); it does not set or measure physical RF power. Check the [output and band limits](docs/reference/output.md) before choosing a frequency or antenna connection.

Optional [LPF / band selector controls](docs/configure.md#lpf-and-band-selector) select an external filter before amplifier enable and release it after amplifier disable. A job must fit one declared filter across all of its RF frequencies. Fixed/manual filtering remains the default.

Timed starts use **UTC**, Coordinated Universal Time. A reachable network time server or a supported controller-time connection supplies the clock. Radio-frequency correction is a separate adjustment: a synchronized clock does not measure carrier-frequency accuracy. See [Time and frequency correction](docs/reference/time.md).

Only one controller can hold the transmitter at a time; that controller is the job's **owner**. Closing a browser or disconnecting a controller does not stop an accepted job. Use the [stop controls](docs/operate.md#status-stop-and-connection-loss) and confirm inactive output; disable and apply standalone schedules separately to prevent later automatic starts. Use a trusted local network and read the [access and security guidance](docs/reference/security.md).

## Development and contribution

Engineering material lives in `engineering/`, outside the [published operator manual](https://wsprrypico.readthedocs.io/en/devel/):

- [Project contract](CONTRACT.md)
- [Architecture](engineering/architecture.md)
- [Development guide](engineering/development/README.md)
- [Selected work](engineering/development/consolidated-backlog.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Original contributions use the [MIT License](LICENSE.md).
