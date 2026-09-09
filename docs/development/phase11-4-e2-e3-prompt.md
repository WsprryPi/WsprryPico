# Phase 11.4 E2/E3 execution prompt

Complete bounded physical hostname-conflict and recovery acceptance using the
single available Pico and an explicitly scoped host alias responder. Start from
Pico `9f9cc8d` on devel, inspect current state and preserve user work. Read the
project contract, architecture, acceptance matrix, mDNS wrapper and pinned lwIP
conflict tests. Retain failed attempts and distinguish host evidence from
physical observations. This cannot close E1 independent two-board identity/trust.

Use only Pico 2 W serial `0BF4B4AEC9FFB344` on wspr5, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, standard inhibited firmware. Refresh INFO,
HELLO/CAPS/STATUS and verified HTTPS before mutation. Require deployment match,
healthy storage, disabled schedules, inactive/unowned state and usable UTC.
Bind firmware, boot, server/client certificate, configured/advertised hostname,
addresses, interfaces and exact request/job identities in private evidence.

Prepare a bounded host responder on wspr5's actual LAN interface, claiming only
`wsprrypico-0a60df.local` at wspr5's own address. Use ordinary mDNS UDP packets
from that host, not forged Pico addresses. Preserve all installed services,
router/DHCP settings, hostnames, trust stores and unrelated discovery records.
Limit advertisements and runtime; announce withdrawal on normal and exceptional
exit. Capture exact-name mDNS observations and Pico-related traffic with bounded
processes. No new certificate, flash, GPIO or RF operation is required.

1. **E2:** establish a verified TLS owner and submit one complete CAPS-valid
   finite inhibited job. Observe Running before starting the conflicting
   claimant. Record packets from both addresses, actual device conflict state,
   empty advertised name, unchanged configured certificate name and absence of
   an automatic suffix. Observe the original job/owner/boot throughout and
   authoritative matching completion without another LOAD/ARM. Confirm TLS
   still authenticates the original device using its known IP plus expected
   DNS identity. Do not infer conflict or completion from failed resolution.
2. **E3:** stop and withdraw the claimant, prove its traffic ceased, and check
   that conflict remains latched before explicit retry. After matching terminal
   and inactive/unowned cleanup, issue authorized Console WIFI OFF then WIFI ON.
   Capture fresh probing and announcement of the same certified alias at the
   Pico's current address. Verify active state, no suffix, matching device/boot,
   unchanged configuration/schedules/watermark, and fresh Mac/Linux resolution
   plus authenticated HTTPS. Preserve any cache or TCP delay separately.

Use one persistent USB inspection session to avoid exhausting resumable-session
capacity. Treat lost transport observations as unknown until independent
authoritative status resolves them. On failure stop the claimant and dependent
mutations, verify output, perform only authorized owner/Console cleanup, and
restore Wi-Fi after idle recovery. Keep credentials, captures and generated
runtime artifacts owner-only and out of source control.

Repair actionable in-scope findings. Run existing portable and actual pinned
lwIP responder tests where relevant, independently audit packet/evidence claims,
and test the audit's refusal of corrupted or insufficient evidence. Repeat the
adversarial assessment after corrections. Update results, hash manifest, matrix
and development entry points; preserve narrower scope and remaining gates.
Review the final staged diff, commit and push to origin/devel, verify clean
remote parity, and report outcomes with the remaining-items table.
