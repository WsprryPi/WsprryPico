# Management DNS-SD

Pico station mode publishes its current management service as `_http._tcp` on
port 80, with exactly `txtvers=1`, `product=WsprryPico`, and
`management=Consumer-Radio/1`. The certified hostname and authenticated device
identity remain separate from the operator's display name. Discovery is a hint;
management verifies the current device, boot, profile, contract, and revision
before mutation.

No shipped image publishes `_wtp._tcp` or a WTP binding. Saved WTP observations
do not authorize a management connection or execution fallback. Certificate
HTTPS and encrypted Consumer-Radio retain their independent security policies.
See [network control](../development/network-control.md) and
[native execution](Native-Execution.md).
