# Raspberry Pi/Linux BLE local-control client

`scripts/wsprrypico_ble.py` is the supported native BlueZ client for the
existing WsprryPico Phase 12 GATT service. It gives a Raspberry Pi the same
encrypted, application-authorized local-control path used by the checked-in
Bluefy page without adding another device protocol or job service.
The UUIDs, framing, authorization exchanges, provisioning vocabulary and WTP
mapping are defined by the frozen
[Field-GATT/1 protocol and super-user guide](../protocol/Field-GATT.md) and its
[machine-readable conformance vectors](../protocol/Field-GATT-v1-vectors.json).
Firmware, Bluefy and this client are source/host conforming to that contract.
Physical native-Pi profile activation remains an open Phase 12 acceptance row.

This tool is an additional local/bench client. Bluefy remains the selected
iPhone client, and a Raspberry Pi run is not evidence for Bluefy/iOS offline
acceptance. For normal remote job transfer and job control, authenticated
TLS/TCP remains a first-class WTP transport. USB CDC remains the canonical
reference transport. All three carry complete jobs to the same device
`JobService`; symbol timing never depends on BLE, USB or network packet timing.

## Prerequisites and security boundary

The client uses the system BlueZ D-Bus API. Raspberry Pi OS needs BlueZ,
`python3-dbus` and `python3-gi`, a powered controller such as `hci0`, and a user
authorized by the OS to pair and connect. The client imports those modules only
when it opens a real BlueZ session; its protocol tests have no Bluetooth
dependency.

Before connecting, obtain both of these values through an already trusted
inventory or the explicit USB-local recovery/inspection path:

- the controller's exact Bluetooth address; and
- the full 32-lowercase-hex WTP device ID.

The advertising suffix is not an identity. The client selects only the supplied
address, then reads the encrypted identity characteristic and rejects the
connection unless its full device ID matches. It never sets BlueZ `Trusted` and
never removes another bond. Its transient `NoInputNoOutput` pairing agent is
unregistered when the command exits. A successful first authorization promotes
the target-side provisional bond under the existing access policy; later
commands preserve and reuse that bond.

Just Works protects the link but does not authenticate against an active MITM
during first pairing. Open the target's 120-second enrollment window only while
physically controlling the intended device. On the existing authenticated USB
Console CDC, with the target proved idle and output inactive, issue:

```text
ACCESS ENROLL <full-device-id>
```

The client cannot open enrollment through BLE. Outside that window a new peer
fails closed, while an already authorized retained bond may reconnect normally.
The application password is read from a non-echoing terminal prompt; there is
no command-line, environment-variable or file option for it. The CLI prompts
for authorization even on a retained bond, but the target does not validate
that field during retained-bond reauthorization. For `provision`, the CLI then
prompts a second time immediately before profile apply. Only that second entry
is sent as the fresh, transaction-bound `profile_step_up` proof. It authorizes
only the exact staged profile, apply request and observed generation; it does
not authorize password, bond, trust or reset mutation.

If enrollment expires while a provisional link remains open, the target erases
the provisional bond, invalidates its authority and requests link closure.
Clients still disconnect promptly after rejection or timeout rather than
keeping a failed session alive.

## Commands

Run from the repository checkout on the Raspberry Pi. Replace both illustrative
identities in every command:

```sh
python3 scripts/wsprrypico_ble.py \
  --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  inspect
```

`inspect` is intentionally limited to an already-paired controller. It verifies
the encrypted identity characteristic and prints only the address, full device
ID and current profile generation; it will not create a provisional bond that
is then abandoned without application authorization. For first enrollment, run
one of the authenticated commands below while the enrollment window is open.
They prompt for the application password:

```sh
python3 scripts/wsprrypico_ble.py --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa status
python3 scripts/wsprrypico_ble.py --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa identify
python3 scripts/wsprrypico_ble.py --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa sync-time
python3 scripts/wsprrypico_ble.py --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa wtp-status
```

`sync-time` uses the same principal/session/device/nonce-bound challenge as
Bluefy. The target begins charging latency when it starts the final challenge
response indication, a conservative boundary before the controller can first
sample UTC. The Linux client sends the ordered `time_submit` fragments with the
encrypted GATT write-without-response property so per-fragment ATT replies do
not consume that fixed budget; the bound response indication remains the
end-to-end success/failure result. Missing or reordered fragments still time
out or fail closed, and the fixed uncertainty ceiling is unchanged.
`wtp-status` subscribes
to the separate encrypted GATT WTP endpoint,
negotiates `WTP/1`, verifies device and boot identity, and requests `STATUS`.
It proves the local client can carry the unchanged WTP stream; it does not start
a job. The CLI intentionally exposes no RF-starting shortcut.

Use `--adapter hci1` only when the exact controller is known to be on another
adapter. `--timeout` accepts a positive value no greater than 120 seconds; the
default is 30 seconds. A command disconnects on exit but retains the BlueZ and
target bonds.

## Atomic profile transfer

The native client implements the frozen Field-GATT/1 profile workflow. Its
source/host conformance is accepted; use on a physical target remains subject
to the open Phase 12 native-Pi profile-activation acceptance row.

The input is the existing canonical version-1 profile, not a new Linux-specific
format:

```json
{
  "version": 1,
  "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "wifi": {
    "ssid": "example",
    "password": "replace-this",
    "time_server": "time.local"
  },
  "tls": {
    "hostname": "wsprrypico-0a60df.local",
    "port": 18443,
    "server_certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
    "server_private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
  }
}
```

Keep the real file outside Git. It must be an absolute,
nonsymlink, regular file owned by the invoking user with no group or other
permission bits and no more than 7,168 bytes:

```sh
chmod 600 /absolute/private/path/profile.json
python3 scripts/wsprrypico_ble.py --address AA:BB:CC:DD:EE:FF \
  --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  provision --profile /absolute/private/path/profile.json
```

The client validates and canonicalizes the entire profile, requires its device
ID to match the connected target, transfers ordered 64-byte fragments, binds a
fresh password step-up to the exact profile session, apply request and observed
generation, and attempts a bounded cancel after any post-open failure. The
target admits the full 7,168-byte contract limit, including one-byte
fragmentation; 64 bytes is the client-preferred chunk size, not a lower 4,096-
byte ceiling.

When the public default password is active, the target also requires the
identity-bound USB command `ACCESS CONFIRM PROFILE <full-device-id>`. The client
prints that instruction and polls the bound step-up status for at most 25
seconds, within the 30-second profile-session lifetime. A timeout fails closed
and cancels the staged transaction.

The client never prints the profile, Wi-Fi password, private key or application
password. Python cannot guarantee destruction of every immutable interpreter
copy, so the process remains a secret-bearing endpoint; use an owner-controlled
host and terminate it after use.

## Failure and recovery

Stable error names are printed without target payloads or secrets. Wrong
identity, malformed/duplicate/out-of-order frames, WTP CRC or response mismatch,
authorization rejection and timeout all fail closed. Pairing failure commonly
means the enrollment window is closed, target bond capacity is full, the wrong
address was supplied or OS policy denied pairing. Check target `ACCESS STATUS`
over the authenticated USB Console and the local BlueZ service; do not weaken
the device policy or mark it trusted as a workaround.

If a profile apply response is accepted, network activation follows the target's
existing delivery-safe boundary. Reconnect and verify the new generation and
safe device state through an authorized path. A lost BLE connection, missing
reply or process exit is never evidence that RF output is inactive.

## Evidence boundary

`tests/raspberry_pi_ble_client_tests.py` deterministically covers framing,
identity binding, authorization, field controls, WTP negotiation/status, the
bound step-up/apply transaction, confirmation polling, cancellation, the exact
7,168-byte transfer and local file controls. The vector-driven provisioning
contract check keeps firmware, Bluefy, Linux, documentation and the frozen
limits synchronized. The bounded
[execution record](phase12-pi-ble-tcp-review.md) adds exact `wspr5`/Candidate A
RF-inhibited evidence for identity inspection, controller-time submission,
field status and WTP `HELLO`/`STATUS`; all other deterministic results remain
source/host evidence. The live subset does not qualify RF, SoftAP, Bluefy/iOS,
profile activation, radio coexistence, TCP interoperability or general release
behavior. In particular, this source freeze does not retroactively turn the
historical live subset into native-Pi profile-activation evidence.
