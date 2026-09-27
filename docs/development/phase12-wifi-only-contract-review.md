# Wi-Fi-only bootstrap contract adversarial review

Status: **SIXTH DESIGN ASSESSMENT COMPLETE; IMPLEMENTATION AND TARGET GATES OPEN**.
Date: 2026-09-26. Scope: the
[execution prompt](phase12-wifi-only-contract-execution-prompt.md),
[product proposal](phase12-wifi-only-bootstrap-proposal.md),
[proposed wire contract](../protocol/WiFi-Bootstrap-v1-proposal.md),
[synthetic vector](../protocol/WiFi-Bootstrap-v1-vectors.json),
[feasibility record](phase12-wifi-only-feasibility.md) and roadmap wording.
No credential-accepting firmware, browser form or target join was reviewed.

## First assessment and repairs

| Finding | Repair |
| --- | --- |
| The existing RF build runs a flash-using second core. Copying Raspberry Pi's BOOTSEL polling example would temporarily detach flash CS without coordinating it. | The feasibility record names the SDK flash-safe critical zone and requires a RAM-resident callback, exact CS restoration, coordination failure rejection and target timing/radio measurements. No sampler was added. |
| The proposal left nonce, request-ID and transcript encodings to implementation; independent clients could derive different keys or AAD. | The proposed wire contract fixes exact JSON fields, fixed-length binary transcript, HKDF info, plaintext and base64url/hex encoding; a reproducible synthetic vector now includes a known RFC 7748 X25519 shared secret. |
| The old P12.10 text used generation 1 for full commissioning even if network-only setup consumed it. | The roadmap now distinguishes a direct blank full-profile generation 1 from network-only generation 1 followed by full-profile generation 2. The two flows cannot share one asserted generation. |
| A public `granted` state could belong to another browser slot, causing a page to expose the password form at the wrong time. | Status now includes a slot-ID digest; the page must compare it to its own slot before showing the form. The digest is not write authority. |
| The initial slot teardown rule removed all key material at commit, yet the proposed browser acknowledgement needed verification afterward. | The contract now permits only a bounded expected acknowledgement verifier and request digest after commit; it clears X25519 private material and plaintext after submit and clears the verifier on acknowledgement, timeout or reboot. |
| A minimum ciphertext length of 19 bytes incorrectly excluded the shortest valid 1-byte SSID plus 8-byte password encoding. | Corrected to 11 bytes and regenerated the vector. |
| Generic `getRandomValues` support and a package README do not prove crypto works in the selected iPhone captive sheet or Safari over HTTP. | The feasibility record limits the noble family to a candidate, requires pinned provenance and a local bundle, and leaves actual iPhone feature/self-tests open. The form cannot request a password when those checks fail. |

## Second assessment and repair

The second reading found proposal prose still describing the encrypted
plaintext as JSON and the start reply as a monotonic deadline, while the
versioned wire contract uses length-prefixed binary credentials and
remaining-time hints. It also omitted the slot digest and bounded
post-commit acknowledgement verifier from the short summary. Those sentences
were corrected before the final assessment.

## Third assessment and repair

The staged diff review caught a lifecycle contradiction: it said to clear
plaintext immediately after submit even though trial association and journal
commit still need it. The contract now clears the X25519 private key after
derivation and clears plaintext plus the AEAD key after the terminal trial
and commit/failure path, retaining only a bounded acknowledgement verifier
after a successful commit.

## Fourth assessment and repair

The next pass found that the route table called for an exact submit/ack
`state` field without enumerating its values or generation meaning. The
wire proposal now fixes `checking`, `connected`, `failed` and the valid
acknowledgement state, with generation 0 versus durable generation 1. The
reassessment also clarified that `checking` may carry generation 1 after
commit if connectivity drops; `failed` is a precommit outcome only.

## Fifth assessment and repair

The later roadmap pass found its short P12.7 row said "before code changes",
which could be read to forbid even a synthetic vector generator. It now says
"before commissioning implementation", consistently with the milestone's
explicit no-commissioning-code gate. The older proposal review now points to
this corrected contract record.

## Sixth assessment

The corrected contract has a coherent one-slot authority flow and exact
cryptographic transcript. A passive AP listener sees the HTTP page and public
keys, but not the encrypted station credential plaintext. An active nearby
party can replace the page, relay the physical interaction or alter the key
exchange. This is the operator's selected limit and must remain visible in
the approval text. The public slot and request digests reveal only bounded
correlation, not a grant or credential. Duplicate and late submissions must
be refused even if HTTP responses are lost; the status route supports
reconciliation without replaying a write.

The main implementation hazards remain **gates**, not closed findings:

- Inspect the actual RAM callback and generated machine code; prove flash/XIP
  and exact CS restoration on the admitted production topology. The
  [target gate](phase12-wifi-only-bootsel-gate.md) failed with a held button
  and a flash-reading core 1, then passed with press/release and concurrent AP
  traffic in the core-1-absent RF-inhibited standard image. The design now
  excludes core-1/RF builds from BOOTSEL sampling; any future second-core
  topology requires a new target gate. Continue to measure CYW43/DHCP/HTTP
  effects when the credential route is eventually enabled.
- Pin, vendor and license the browser crypto bundle; verify its output
  independently against the synthetic vector and prove `getRandomValues`,
  Origin/header behavior and the full encrypted form in the selected iPhone
  captive sheet and Safari at the real HTTP origin.
- Implement and fault-test a distinct network-only journal source. Prevent
  tombstone/corrupt-journal fallback to legacy Wi-Fi, full-profile parser
  confusion, station TLS/job/scheduler startup and any RF permission.
- Prove AP/STA coexistence, association/DHCP, durable readback after reboot,
  terminal response or unknown-state reconciliation, AP withdrawal and
  read-only fallback on the exact RF-inhibited target image. A Pi-only client
  cannot close the iPhone browser gate.
- Obtain operator acceptance of the complete Wi-Fi-only exception to the
  current blank-AP read-only contract before implementing the mutating routes.
  The separate owner/Bluefy P12.7 path remains paused and unapproved.

No further source or document correction was found in this sixth assessment.
The existing read-only AP remains the only implemented blank-device behavior.
