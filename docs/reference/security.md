# Access and security

Use the Pico's browser controls on a trusted **local network**, such as your own home network. The page opens over **HTTP**, the web connection beginning `http://`, on port **80**. A port is a numbered connection endpoint; no extra port number is needed in the Pico's ordinary browser address.

The page uses the **Pico password**, which defaults to the saved home Wi-Fi password. You can [set a separate Pico password](../maintain.md#change-the-pico-password). Login and control messages are encrypted by the application, but **HTTP does not authenticate the page delivered to your browser**. Someone who can substitute that page can steal a password entered there. Keep the Pico on a trusted network and do not expose its control services through Internet-facing router port forwarding.

A browser login expires after **30 minutes without an authenticated request** or **8 hours total**, even while actively used. Leaving the page open, typing or scrolling alone does not keep it signed in. Automatic status checks while this tab tracks an armed or running job can renew idle time. Select the unlocked icon beside the hostname to lock this browser when finished; closing or reloading a tab may leave its login occupying one of the Pico's three slots until expiry. [Login retirement](../maintain.md#recover-an-occupied-login) can free an occupied slot sooner. A restart, Pico password change, network-context change or an unconfirmed request can still require signing in again. Signing out or expiry does not stop an accepted transmission.

**Setup Wi-Fi** is the temporary open network broadcast by the Pico. Joining it requires no Wi-Fi password. On a configured Pico, opening the control page still requires the Pico password. The separate [recovery page](../maintain.md#recovery-and-reset) allows destructive resets from that setup network without a browser login; anyone connected to it can reach those reset controls.

**WTP**, the WsprryPi Transmitter Protocol, is the job-control connection used by controllers such as WsprryPi. **Plain LAN** means the ordinary, unencrypted local-network WTP connection on TCP port **31417**. It accepts reachable clients after the Pico has joined the network and obtained acceptable time; it does not use the Pico browser password. Restrict network access to trusted controllers. Engineering connections using TLS encryption and certificates are configured separately and do not automatically fall back to Plain LAN.

USB management relies on physical access to the cable and device. It can change saved settings without the browser password; ordinary management access does not take over an existing job. The [USB Console stop command](../usb.md#stop-output-from-the-console) is an explicit physical shutdown control.

The **full device ID** identifies a Pico. Its hostname and ID help you select the correct device; they are not passwords. Saved configuration and full-flash backups can contain Wi-Fi passwords, keys and other private data. Keep those files private and do not assume flash memory encrypts them. Remove secrets from screenshots, URLs, issue reports and logs before sharing.

To report a vulnerability, follow the repository's [security reporting instructions](https://github.com/WsprryPi/WsprryPico/blob/devel/SECURITY.md).
