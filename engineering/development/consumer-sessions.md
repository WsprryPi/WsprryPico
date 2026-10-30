# Consumer sessions

## Quotas and isolation

Three fixed session slots support phone, Mac and native Pi simultaneously at the
same station authority. At most one slot may hold a pending login; pending and
active slots together cannot exceed three. A pending login reserves its eventual
active slot. Full capacity returns 409 `radio_session_capacity`; an occupied
pending quota returns 409 `radio_login_pending`. Successful starts remain globally
spaced by one second (429). No eviction or automatic mutation retry occurs.

Each slot owns binding, interface/origin, timestamps, sequence, one outstanding
transaction and a distinct injected crypto object. Production statically constructs
three noncopyable crypto objects; handles are never copied or moved. At most one
ephemeral PSA key is retained, because only pending logins retain one. Active
sessions retain two 32-byte traffic keys and transcript state; PSA lifetime stays
reference counted. Crypto scratch is transient on serialized core 0. Fixed object sizes exclude dynamic buffers, allocator overhead and library heap.
They do not establish target heap or stack high-water.
No session retains request/response pages: these belong to the unchanged two TCP
tasks. Two large exchanges still require existing memory admission and the 32 KiB
authority reserve; capacity does not promise two maximum-size replies can allocate.

Lookup requires a bounded CR01 header before using its ID as an untrusted selector.
The selected slot must match state, context, sequence and complete AEAD. IDs use
a random prefix and a nonreused boot-local 64-bit serial suffix. Zero, RNG failure,
raw occupied-ID collision and serial exhaustion fail closed without retry loops.
Expiry and every local failure close only the selected slot. Generation, unhealthy
profile and global admission invalidate all affected slots. AP withdrawal and
station address/hostname changes invalidate only the matching interface. Normal
TCP closure leaves login state intact. Nonreused transport transaction identities
route delivery completion across slot reuse, without duplicating board effects.

## Duration and compatibility

Authenticated requests renew a thirty-minute idle interval. The eight-hour absolute lifetime starts at successful login and never renews. Public requests, page visibility and editing do not renew idle time. Existing armed/running-job status polling may renew it; no general keepalive is added. Closing or reloading a tab can abandon a server slot until expiry. Explicit logout and authenticated retirement can free it sooner.


Updated Pi adapters accept network /1, /2 and /4, or USB /3 and /5, with exact fields, integer limits and matching capability references. Their local consumer deadlines come from the authenticated, validated management document. Older Pi adapters explicitly refuse /4 and /5. An old browser bundle may still end its own login at the historical limits; reload the page from the updated firmware. Unsupported versions and mismatched policies refuse without fallback, eviction or automatic mutation retry. Consumer-Radio/1 bytes/vectors stay unchanged.
