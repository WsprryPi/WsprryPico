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

Network management discovery uses closed `transmitter-management/2`, keeping the old
shape and all old limits except `consumer_sessions:3`, and adding integer
`consumer_pending_logins:1` in limits. Version 1 remains frozen. Compatible Pi adapters accept
exact versions 1 and 2 with their exact limits/types. Older adapters refuse version 2;
there is no fallback or downgrade. Consumer-Radio/1 bytes/vectors stay unchanged.
