# Security reporting

Report a suspected vulnerability privately to the project maintainer. Request a private contact channel without posting exploit details publicly. Include the affected revision, board and firmware identity, transport, reproduction conditions, expected and observed behavior, and any hardware or RF involvement. Remove credentials and other private data from reports.

Security-sensitive areas include USB/TCP parsing, bounded job storage, ownership, replay handling, Wi-Fi/BLE provisioning, browser mutations, firmware integrity and failures that leave output active. Reproduce hardware conditions only within an authorized, bounded setup.

The consumer browser uses the Pico password to authenticate encrypted application traffic. That password defaults to the saved Wi-Fi passphrase unless a separate Pico password is configured. HTTP does not authenticate the page that supplies the encryption; an active page-substitution attacker can steal the entered Pico password. Default consumer Plain LAN WTP permits clients that can reach station TCP port 31417 after accepted network time. Network reachability is its trust boundary. Engineering mutual TLS has separate credentials and is disabled by default. See [certificate management](engineering/development/network-control.md) for renewal and compromise recovery.

Engineering BLE uses Just Works pairing plus an application password. Its station-MAC-derived default is observable and convenience-only. Changing it reduces casual nearby access but does not protect Just Works against an active intermediary. Sensitive trust/reset mutations require a fresh password and, while the public default remains active, physical or USB confirmation. USB management relies on local physical access independently of network passwords. Ordinary flash storage provides no confidentiality guarantee.

Never publish passwords, access-sector contents, private keys, credential-bearing firmware or generated private build headers.

The consumer operator page exposes a read-only public transmitter projection at `/api/consumer/v1/status`: device/boot identity, job state, RF output activity, whether the transmitter is reserved, clock state/time/uncertainty and engine. Owner IDs, job IDs, messages, settings, history and credentials are omitted. Host and same-origin request checks remain enforced; public reads do not authenticate a browser or renew a login.
