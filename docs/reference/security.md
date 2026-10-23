# Access and security

Use consumer control on a trusted network. Its HTTP page authenticates the
Pico password (the saved Wi-Fi password by default) and encrypts application traffic, but **HTTP does not
authenticate the page delivered to your browser**. An active attacker who
substitutes that page can steal a password entered there.

Plain LAN WTP at TCP **31417** accepts reachable clients after station
connectivity and accepted network time. It does not use the browser password.
Keep untrusted clients away from that port. USB control relies on physical
access. Engineering mutual-certificate TLS is a separate profile and has no
automatic downgrade.

The full device ID distinguishes devices; a hostname alone is not an access
credential. Ordinary flash provides no confidentiality guarantee. Keep
configuration files, certificates and full-flash backups private. Do not put
passwords in screenshots, URLs, issue reports or public logs.

To report a vulnerability, follow the repository's
[security reporting instructions](https://github.com/WsprryPi/WsprryPico/blob/devel/SECURITY.md).
