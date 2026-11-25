# Management DNS-SD

Pico station mode publishes its current management service as `_http._tcp` on port 80, with exactly `txtvers=1`, `product=WsprryPico`, and `management=Consumer-Radio/1`. The certified hostname and authenticated device identity remain separate from the operator's display name. Discovery is a hint; management verifies the current device, boot, profile, contract, and revision before mutation.
