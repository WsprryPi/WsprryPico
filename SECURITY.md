# Security reporting

There are no published releases or implemented firmware targets yet.
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
