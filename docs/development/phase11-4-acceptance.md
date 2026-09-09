# Phase 11.4 opt-in inhibited device acceptance

Status: Phase 11.4 OPEN. Use the [joint plan and case matrix](phase11-4-plan.md)
and [current review](phase11-4-review.md) for actual attempts and remaining gates.
This procedure was NOT EXECUTED by Phase 11.3. Every device,
USB, flash, router/DHCP, trust-store or service action below requires explicit
separate authorization. Do not run it as part of host CI. Use only the inhibited
image; no GPIO/RF or StandaloneRF operation is authorized by this document.

## Current standalone inspection

The standard target uses a JSON Console and CAPS engine
`inhibited-standalone-simulator`. It can acquire SNTP and simulate finite
Armed/Running lifecycles while always reporting inactive output. Do not use the
historical `check_usb_target.py` as this image's acceptance oracle: it requires
the early text banner, `inhibited-no-rf` and an unsynchronized clock.

After exact USB authorization, use the existing bounded commands on the client
where the identified endpoints are attached:

```sh
python3 scripts/standalone_console.py info --port "$CONSOLE" --device-id "$DEVICE_ID" --run
python3 scripts/standalone_console.py status --port "$CONSOLE" --device-id "$DEVICE_ID" --run
python3 scripts/wtp_probe.py "$WTP" --run
```

Resolve these variables from verified USB serial/interface metadata and the
approval record. Add `--revision` once the current revision is established.
The probe checks framing/schema/request identity but does not enforce the
expected board, engine or output state. Cross-check HELLO device/boot with
Console, CAPS with the exact inhibited image, and STATUS with inactive/unowned
state. Its resynchronizing decoder is not a strict USB-byte-isolation test.
Console INFO exposes engine and boot under `status`; revision is top-level.

Build only `cmake --build <approved-build> --target WsprryPico`, then run
`python3 scripts/check_standalone_image.py <approved-build>/firmware/WsprryPico.elf`.
This checks endpoint layout plus standalone UF2/journal bounds. Separately
inspect CMake definitions, linked engine symbols, embedded revision and deployment
identity: passing a layout check alone proves neither inhibition nor board binding.

The joint matrix expands the steps below to cover cancellation/foreign ownership,
request loss, process restart, USB versus Console authority, persistence and final
cleanup. Missing equipment remains BLOCKED. Injected DNS, host packet simulations
and preview proxies are not physical mDNS/browser/two-board acceptance.

Expired server credentials are rejected by the production build validator;
that is build-layer evidence. Plan invalid/expired client tests with valid device
time/server/CA inputs so the intended layer is reached. Never disable checks or
falsify clocks. Issuing a replacement client certificate does not revoke an old
valid one; per-device CA replacement is the existing compromise-recovery mechanism.

## Record the acceptance identity

Create a private evidence directory outside tracked source. Record both source
revisions, firmware ELF/UF2 hashes, Pico board and full WTP device ID, inhibited
engine, clock profile, deployment.json and public certificate fingerprints/SANs,
port, Mac/Linux OS and resolver versions, network/interface and DHCP lease state.
Do not record private keys/passwords. Record authoritative INFO/STATUS showing
output state before proceeding. If status is unavailable, retain output unknown.

1. After authorization for the exact board/image, build using the validated
   hostname deployment bundle and the documented inhibited target, check its ELF/
   UF2 layout, and flash by the established USB recovery procedure. Record actual
   boot/device identity and `deployment_identity_matches:true`. Verify INFO reports
   inhibited engine and authoritative inactive output; disconnect is not proof.
2. After explicit trust authorization, import only this device CA and the separate
   browser PKCS#12 identity. Open `https://<hostname>:<port>/`. Record browser name,
   TLS certificate DNS SAN/issuer/validity and client-certificate selection. Reject
   certificate-warning bypasses. Confirm one persistent WTP client plus browser
   read/status, then revision-controlled idle config/network management. Do not
   load or arm a physical-output image.
3. Check actual resolver paths on the intended clients, using the known hostname:

   ```sh
   dns-sd -G v4 <hostname>              # macOS; Ctrl-C after recording result
   getent ahostsv4 <hostname>          # Linux system NSS path used by getaddrinfo
   resolvectl query <hostname>         # if systemd-resolved is installed
   avahi-resolve-host-name -4 <hostname> # if Avahi tooling is installed
   ```

   Record available tools, failures, resolved address and interface. A tool absent
   is not a pass. Do not install/reconfigure services or edit hosts/NSS implicitly.
   Preserve each command's own exit status; a later successful inventory command
   must not hide a failed lookup. For a bounded `dns-sd` capture, use a terminal or
   otherwise ensure stdout is flushed before stopping it. An `active` device
   diagnostic does not prove peers can resolve the name. Retain failures that
   recur after an apparently successful retry.
4. With separate router/DHCP authorization, cause a real lease/address reassignment
   and record old/new addresses and packet evidence where permitted. Wait through
   reprobe/cache update, reconnect WsprryPi and reload the hostname browser URL.
   Assert same certificate fingerprint and WTP device ID, changed resolved address,
   no duplicate LOAD/ARM, and no false inactive output after failed reconnects.
   Verify the old address is no longer advertised by this device. Record any peer
   cache delay; absence of local registration does not prove peer caches emptied.
5. With authorization for each additional board, test two distinct default names.
   Then intentionally deploy duplicate aliases using separate per-device CAs and
   proper certificate DNS SANs. Verify conflict is reported, advertised name is
   empty, no suffix rename occurs, and an executing inhibited finite job is not
   interrupted. Resolve the duplicate, then issue idle USB `WIFI OFF` and `WIFI ON`
   to retry. Record which board wins probing and all failures; do not assume it.
6. Test orderly idle disable and reconnect, plus independently authorized access-
   point/link loss. Record goodbye send attempts separately from observed packets;
   never claim a goodbye after the link disappeared. Verify probing and coherent
   current address on reconnect, without resource growth across repeated cycles.
7. Issue server renewal into a new directory using the same device ID/hostname,
   validate, and explicitly authorize rebuild/reflash. Confirm client CA trust
   remains, DNS SAN stays fixed and DHCP config is unchanged. Negative cases:
   wrong hostname, wrong CA, expired certificate, missing client certificate,
   wrong-board bundle and literal IP absent from SAN must reject. For explicit IP
   plus expected hostname, verify WsprryPi still authenticates the DNS SAN and
   sends hostname Host/Origin. A literal-IP browser URL succeeds only with IP SAN.
8. Lose a response during an inhibited complete finite job and reconnect. Observe
   original device/boot/session and reconcile through WTP STATUS without automatic
   duplicate LOAD/ARM. USB recovery must use the authoritative state and existing
   ownership/abort/release rules. If output cannot be proven inactive, record unknown
   and stop dependent actions. Preserve every failure and its later disposition.

## Exit evidence

Before production-host invocation, inspect the actual application's singleton
policy as well as web/socket ports. The reviewed Pi executable reserves port
1234 before ordinary startup; selecting different web ports does not permit a
second instance alongside an installed service. Use a suitable separate client,
or prepare a separately authorized service pause/restart after establishing that
service's own authoritative output and restart behavior. Do not bypass the
singleton or stop an unrelated active service as incidental test preparation.

Record final INFO/WTP STATUS, local/peer name observations, browser trust outcome,
resolver evidence, resource diagnostics, tested revisions/hashes and unresolved
items. Restore only explicitly authorized operational changes. Phase 11.5 still
owns measured target heap/stack/fragmentation and contention; 11.6 owns conducted
RF; 11.7 owns final joint closure. Inhibited acceptance does not qualify RF.
