# Session recovery

## Selected design

WsprryPico leads; WsprryPi adopts the same separately versioned
Consumer-Recovery/1 extension. Consumer-Radio/1 traffic, its fixed vectors and
the frozen management/1 and management/2 discovery documents stay unchanged.

Recovery retires one explicitly selected login and never creates a replacement
session or repeats an application request. The operator supplies the current
Pico password (the saved Wi-Fi password by default) for a fresh authenticated exchange. A retained nonsecret
retirement selector identifies the affected login after traffic-key loss; it is
not a retirement credential. It is a domain-separated one-way alias of the
raw traffic ID, device and boot; discovery never publishes traffic IDs. An alias
cannot address an ordinary CR01 request or consume a pending login proof.
With no retained selector (fresh page/process or
lost start reply), public recovery discovery lists occupied selectors and their
interface/authority/state. The UI must show that the selected login could belong
to another operator and require an explicit retirement action. Shared-password
membership cannot identify the original owner. No automatic eviction is allowed.

GET `/api/consumer/v1/recovery` returns closed `consumer-recovery/1` metadata,
current device/boot/generation and at most three occupied selectors. These are
untrusted handshake hints, not authenticated private state. Discovery and
retirement are restricted to the same exact authority and interface as the
victim; IP, hostname and optional `:80` sessions are distinct. The client
compares the grant with its independently selected transport context. POST
`/api/consumer/v1/recovery/start` carries ordinary identity/key/nonce fields,
`version:1` and `target_selector`. The grant additionally binds target, exact
HTTP authority and actual interface. The recovery transcript is the existing
radio transcript followed by NUL-terminated
`WsprryPico/Consumer-Recovery/1`, the SHA256 of target (16 decoded bytes), interface byte
(1 AP, 2 station), authority length (one byte) and ASCII authority. The resulting
SHA256 replaces the ordinary transcript digest; unchanged HKDF labels and AEAD
framing therefore operate in a separate cryptographic domain. No recovery key
can authorize an application request. POST `recovery/finish` authenticates the
sequence-zero proof, seals a sequence-zero acknowledgement identifying the exact
target, then retires that target. Every complete proof consumes its challenge.

One dedicated pending crypto workspace exists outside the three ordinary slots.
It never becomes an active session. It expires absolutely after five seconds;
all admitted starts, including RNG/crypto failure, are spaced at least one second apart. One ordinary pending
login and one recovery proof may coexist (at most two ephemeral PSA handles).
Malformed/failed proofs do not touch victims or their timers. Recovery refuses
wrong Host/Origin/interface, stale identity/generation, oversized/duplicate JSON,
invalid keys and failed RNG/allocation/crypto. All workspace keys are erased on
consumption, expiry or context invalidation. No private application reads occur.

A client retiring its own login clears its traffic state before dispatching the finish proof. A lost reply retains only the alias and invalidates saving. A lost recovery reply is reconciled by another explicit authenticated retirement of the same boot-bound target: an absent target returns an authenticated absent result. No slot is allocated and nonreused boot-local session IDs prevent a delayed proof from retiring a new occupant. Abandoned recovery starts can delay another recovery by at most five seconds with healthy transport and no competing new starts. Repeated competing traffic can deny service; no availability guarantee is made against that traffic. No ordinary session expiry or reboot is required. A complete recovery followed by an explicit ordinary login requires four POSTs plus discovery/identity reads; the existing one-second ordinary login pacing still applies. Browser discovery and identity reads each have a five-second timeout; recovery POSTs each have five seconds and ordinary login POSTs each have 30 seconds. Native HTTP exchanges each have an eight-second absolute deadline and check the proof's five-second pre-finish budget. There is no retry loop. A successful finish retires during that dispatch within the server proof lifetime; timeout/refusal is reported explicitly. These are bounded attempts under a healthy transport, not an availability promise under competing traffic.

Retirement cancels only the selected session's still-pending transaction through
the existing false-delivery callback. Already durable settings and accepted jobs
remain. A delayed ACK/FIN/RST cannot deliver that cancelled transaction or a
later board-wide receipt. JobService, STOP, owner, scheduler, journals and RF
authority do not change. Core 0 owns recovery; core 1 timing is unchanged.

## Save reconciliation

Authenticated application refusals preserve authentication and drafts. Transport,
framing and authentication uncertainty clear traffic keys, retain only bounded
nonsecret target/attempt context, and invalidate write eligibility. No request is
replayed. Recovery/login or a healthy status GET alone cannot unlock Save.
Authoritative config/resource readback must acquire fresh exact revisions under
one target context while retaining drafts. The operator reviews saved versus
draft and explicitly enables a new save. Matching current fields prove current
saved state, never attribution of the historical attempt. Credentials stay
volatile and are scrubbed; no recovery material enters persistent storage.

Commissioning keeps its existing sent-once digest/generation receipt and actual
bootstrap dispatch/delivery gates. Failed results retain correctable drafts;
successful readback must preserve unrelated edits. Receipt-only origin
continuations cannot submit. Password changes require an explicit login using
the password valid for the observed profile. No automatic password guesses.

The hostname lock opens the password dialog; occupied-login recovery is a secondary native disclosure within it. Inspection, exact target selection, current-password proof and explicit confirmation remain separate from replacement login. Cancelling the dialog scrubs both password entries. Locking during an application action gates subsequent dispatches immediately and serializes logout after the current bounded operation; it cannot reverse an accepted save or job. A cancelled late successful login is cleaned up before another login is admitted. Unconfirmed cleanup retains only the existing nonsecret selector for explicit recovery.
