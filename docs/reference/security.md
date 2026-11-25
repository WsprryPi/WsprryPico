# Access and security

Use the Pico's browser controls on a trusted **local network**, such as your home network. The page opens over **HTTP** on port **80**, using an address beginning with `http://`. A port is a numbered connection endpoint. No extra port number is needed in the Pico's browser address.

The page uses the **Pico password**, which defaults to the saved home Wi-Fi password. You can [set a separate Pico password](../maintain.md#change-the-pico-password). The application encrypts login and control messages, but **HTTP does not authenticate the page delivered to your browser**. Someone who can substitute that page can steal a password entered there. Keep the Pico on a trusted network and do not expose its control services through Internet-facing router port forwarding.

Reachable clients can read status, accepted messages, job frequencies, saved schedules, station identity, network names, logging destinations, and other redacted settings without a browser login. Passwords, private keys, and certificates are excluded. Public reads do not authenticate a claimed Pico, occupy a login, renew one, or authorize writes. Restrict access to the intended local network.

A browser login expires after **30 minutes without qualifying authenticated activity** or **8 hours total**, even while actively used. Leaving the page open, typing, scrolling, and automatic public status checks do not keep it signed in. Select the unlocked icon beside the hostname to lock this browser when finished. Closing or reloading a tab may leave its login occupying one of the Pico's three slots until expiry. [Login retirement](../maintain.md#recover-an-occupied-login) can free an occupied slot sooner. A restart, Pico password change, network-context change, or an unconfirmed request can still require signing in again. Signing out or expiry does not stop an accepted transmission.

First-time commissioning and deliberate recovery can open **setup Wi-Fi**. Configured field and fallback access use WPA2 with the Pico password. Joining an access point and authenticating to the control page are separate steps. Anyone connected to an open recovery window can reach its [destructive reset controls](../maintain.md#recovery-and-reset).

WsprryPi and the Pico browser manage schedules saved on the Pico through authenticated management. The Pico starts and times each eligible transmission locally. **Stop native schedules** disables saved schedules through an explicit authenticated action. The external button and USB Console provide local shutdown controls. Engineering HTTPS verifies certificates and hostnames and negotiates `http/1.1`.

USB management relies on physical access to the cable and device. It can change saved settings without the browser password. Ordinary management access does not take over an existing job. The [USB Console stop command](../usb.md#stop-output-from-the-console) is an explicit physical shutdown control.

The **full device ID** identifies a Pico. Its hostname and ID help you select the correct device; they are not passwords. Saved configuration and full-flash backups can contain Wi-Fi passwords, keys, and other private data. Keep those files private and do not assume flash memory encrypts them. Remove secrets from screenshots, URLs, issue reports, and logs before sharing.

To report a vulnerability, follow the repository's [security reporting instructions](https://github.com/WsprryPi/WsprryPico/blob/devel/SECURITY.md).
