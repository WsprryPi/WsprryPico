# Use with WsprryPi

Use a WsprryPi version that supports the Pico transport and management features
you need. See the companion manual's
[Pico and Fleet setup](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#add-a-pico-and-manage-outputs).

## USB member

1. Connect the Pico by a USB data cable to the Pi running WsprryPi.
2. In WsprryPi transmitter setup, discover the USB Pico. Compare its full stable
   device ID and reported saved name with the intended device.
3. Add/select that member, review its station, pins, drive and frequency policy,
   and use WsprryPi's schedule/job controls.

USB provides configuration and controller time without Wi-Fi. Administrative
USB access does not take over an existing RF job. Firmware updates use the
**Pico firmware over USB** panel; a member stays paused until verification
and reconnection complete. Review the image branch explicitly: its default is
main even when the Pi itself runs devel.

## Network member

Normal consumer firmware exposes **Plain LAN WTP on TCP port 31417** after
station Wi-Fi connects and network time has been accepted. Use a trusted LAN;
any client able to reach that port can submit commands under its LAN authority.
The browser password is not a WTP/TCP access control. Engineering mutual-TLS
profiles are a separate setup with no automatic downgrade.

## Ownership and schedules

One local job service owns output. A controller sends a complete job before
arming; the Pico owns symbol timing and cleanup. Connection loss does not
release ownership or stop an accepted job. Use its owning controller to abort
and release, then confirm output inactive.

Review Pico standalone schedule enablement when switching to host scheduling.
Do not expect an enabled standalone schedule and a host job to run at the same
time. Host and Pico frequency opt-ins are separate and both must allow an
experiment. Recorded member tests do not establish full fleet parity or all
transport/firmware combinations.
