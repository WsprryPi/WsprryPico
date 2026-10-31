# Web service

## Implementation and resource policy

`PicoHttpServer` provides two fixed cooperative connection tasks on core 0.
It uses no OS threads or RTOS. Raw lwIP callbacks parse/record input and ACKs; foreground polling
dispatches application requests and streams replies. Crypto, BrowserApi,
JobService, the scheduler, revision checks and flash commits retain their one
serialized owner. Core 1 remains dedicated to the RF worker.

| Resource | Bound/behavior |
| --- | --- |
| Port-80 connections | Two across AP and station; excess connections reset without evicting admitted clients |
| Task storage | Compile-time `sizeof(PicoHttpServer) <= 2048`; dynamic response sources, windows and lwIP are excluded |
| HTTP input | Existing 2048-byte headers and 32768-byte body maximum; narrower setup-route limits retained |
| Header admission | Raw-prefix growth requires 5120 bytes of workspace; the completed header separately admits method/path, strings and map nodes using its byte and field counts; both retain the 32768-byte authority reserve, and pressure refuses the connection before allocation |
| Body admission | Existing shared paged-buffer admission; already reserved body pages continue without requiring another header allowance |
| Output | At most one 1024-byte chunk per task per poll; first task alternates each poll; immutable assets borrow flash storage |
| Lifetime | Absolute ten seconds from accept, including partial input and stalled ACKs; traffic does not extend it |
| HTTP exchange | One request/connection, no pipelining or keepalive extension |
| Delivery identity | Monotonic high-bit transaction namespace; stop/start does not reset it; exhaustion fails admission before reuse |
| Other transports | Engineering HTTPS remains two slots; existing aggregate four TCP PCBs, 32 KiB lwIP heap and packet/segment pools remain unchanged |
| Authentication | Three fixed consumer slots, at most one pending login; transport capacity is independent of login capacity |

Large typed job replies use an owned [response generator](response-generation.md)
with a reusable 1,024-byte output window. Consumer encryption can consume that
snapshot incrementally. USB management shares the source and bounded escaping
preparation while retaining its independent framing and explicit ACK. Capability
and application documents use counted paged output; flash assets remain borrowed.

The heap figures are an admission policy and compile-time/source bounds, not
measurements of target fragmentation, transient peak heap, stack or RF latency.
The shared lwIP TCP pool, including closing connections, can refuse admission
before the port-80 task limit is reached. No transport is promised a dedicated
PCB under aggregate overload.

Each task owns its parser, response, offsets, pending ACK bytes, interface and
transaction. Teardown detaches callbacks, securely releases parsed input,
releases response/header storage and clears the slot before invoking application
delivery hooks. lwIP error callbacks never free the already-freed PCB. LISTEN
PCBs use `tcp_close`, and receive callbacks return `ERR_ABRT` whenever teardown
actually aborts their PCB, including a failed graceful close after full ACKs.

New accepts bind to the actual receiving netif. Each poll rechecks interface
admission independently. AP drain closes new accepts while allowing admitted
AP replies until withdrawal or deadline. Withdrawing AP leaves a valid station
connection intact. Page Host values do not select the interface.

Provisioning uses one transaction-scoped delivery receipt for network submit,
network ACK, owner submit or committed owner-status replies. While it is
outstanding, competing raw setup/API calls receive `409 setup_response_pending`;
authenticated setup adapters share the same receipt gate. Static pages and
consumer identity routes can still progress. The captured owner commit flag
survives another tab's dispatch. Only matching delivery can release/cancel the
pending effect, and success requires every header/body byte to be queued and
TCP-acknowledged. FIN/RST alone never supplies that proof. Unrelated partial
connections no longer postpone a delivered trial or restart. Network changes
or reboot can still close other requests; clients retain the existing uncertain
write/readback contract.
