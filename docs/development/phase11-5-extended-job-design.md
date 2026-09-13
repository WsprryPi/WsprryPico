# Selected extended finite-job implementation

Implementation decision for accepted R3-COMPLETE-20260913-v2. Physical acceptance
is pending; this document defines the implementation being built.

QRSS, FSKCW and DFCW message inputs accept at most 32 characters including spaces.
The existing Pi Morse alphabet has a maximum of six elements per supported
character (`?`, `.`, `,`, `-`). The worst 32-character message contains 192 marks,
160 intra-character gaps and 31 inter-character gaps: 383 events in every mode.
The compact browser message compiler adds a one-microsecond final RF-off interval,
so its worst single-message plan is 384 events. Leading/trailing whitespace is
silent and runs of whitespace select one inter-word gap, matching existing Pi
encoding. All characters, including whitespace, count toward the input limit.

The physical/inhibited standalone engine advertises 512 events and 3,600 seconds.
The independent WTP/1 rf-events/1 ceiling stays 512; WTP framing remains 65,536
bytes. Existing CAPS shape and profile list remain unchanged so strict existing
clients continue to negotiate. WSPR framing, station validation and duration do
not change. Arbitrary raw-event jobs have no inferred message-character count.

Finite repetition is bounded expansion. The compiler computes duration and event
count with checked arithmetic before allocating the expanded job. Repeats include
explicit inter-message gaps and the final off interval in the total duration.
Combinations exceeding duration, event or transport capacity are rejected with
the corresponding actual limit; the message is never truncated or silently split.
No repeat or symbol timing is streamed after ARM.

The target browser gains a compact LOAD_MESSAGE operation in the existing
versioned browser API. The server compiles its bounded message/timing request
into the same complete rf-events/1 Job before LOAD/ARM. This is a browser API
addition, not an incompatible WTP profile or increased HTTP limit. It avoids
sending an expanded 383-event FSKCW JSON body through the smaller 32,768-byte
HTTP limit. The 30,000-byte raw-file route remains separately bounded. The
browser previews exact calculated duration and uses the same finite constraints.
The Pi WTP compiler continues sending rf-events/1 within negotiated CAPS and
adds the 32-character validation only on its WTP-facing request path.

RF plan segments move from an inline fixed array to a bounded vector allocated
only during preparation, reserved to the admitted event count and moved into the
engine. This keeps enlarged plan copies off the 16 KiB stacks. The two 16,384-word
waveform buffers remain fixed; RF execution allocates no hour-sized sample data.
Disable releases the prepared plan after authoritative sink stop. Duration and
sample arithmetic remains 64-bit, including 496,800,000,000 samples per hour at
138 MHz. Peak heap, retained copies, preparation and refill deadlines still
require final linked-image and physical R3 acceptance.

The engine retains an incremental SHA-256 digest of the canonical job instead
of another full event vector. Decoded requests own their fields; raw WTP input
and the browser's internal envelope are released before preparation. The WTP
output queue keeps its 16-byte header separately from the encoded response, so
a maximum adjustment reply needs no second full wire-buffer allocation. Partial
writes still share one five-second progress deadline. The browser response also
reuses the encoded response storage. These lifetime changes affect physical
memory and transport acceptance; source tests alone do not qualify them.

HTTP body admission remains exactly 32,768 bytes. Conversion into an internal
WTP envelope is checked against WTP's separate 65,536-byte limit; the conversion
must not subtract its metadata overhead from the advertised HTTP capacity.
Large input admission uses nullable newlib allocation after returning unused
top pages. Allocator timing includes this complete serialized trim/allocation
section. SDK panic behavior for other allocations remains unchanged.
