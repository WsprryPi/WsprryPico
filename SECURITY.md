# Security reporting

There are no published production releases. Experimental firmware targets exist.
A supported-version policy will accompany releases.

Report a suspected vulnerability privately to the project maintainer. When
this repository is published and private vulnerability reporting is enabled,
use its GitHub security reporting channel. No reporting URL is configured yet;
request a private contact channel without posting exploit details publicly.

Include the affected revision, board/firmware identity, transport, reproduction
conditions, expected and observed behavior, and whether hardware or RF was
involved. Remove credentials and other private data from reports.

Security-sensitive areas include USB/TCP parsing, bounded job storage, ownership,
replay handling, Wi-Fi/BLE provisioning, browser mutations, firmware integrity,
and failures that leave an output active. Reproduce hardware conditions only
within an explicitly authorized, bounded setup.

Network control defaults off. See [certificate management](docs/development/network-control.md)
for local CA handling, renewal, compromise recovery and current provisioning
limits. The selected
[Phase 12 field-access/security contract](docs/development/phase12-field-access-contract.md)
now has a hardware-free portable policy/persistence implementation and
cross-linked target candidates; see the
[scoped P12.3 closeout](docs/development/phase12-3-review.md). This is not live or
physical security evidence. Its station-MAC-derived default is observable and
convenience-only; customization reduces casual nearby access but does not add
active-MITM protection to Just Works. Sensitive trust/reset mutations require a
freshly entered local password and, while the default remains active, physical
or USB confirmation. Never publish passwords, access-sector contents,
credential-bearing UF2 files or generated build headers.
