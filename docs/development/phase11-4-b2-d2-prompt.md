# Phase 11.4 B2/D2 execution prompt

Address Linux NSS discovery and repeatable orderly Wi-Fi withdrawal/recovery from
Pico devel f58d303ddc9d8fe8b313df04f888001681f172e5. Read README, CONTRACT,
architecture, current acceptance procedure/matrix and D1-D3/D3 evidence. Preserve
all failed attempts and user changes. The original standard inhibited firmware,
not a test-only image, is the physical baseline. Do not change the router, DHCP
reservations, client trust, system resolver configuration or another repository
as an incidental remedy. The user controls further router changes.

Use only Pico 2 W / RP2350 USB serial 0BF4B4AEC9FFB344 on wspr5, device
fd6127d11d6aca42a9905fa3fb1bf1d5, name wsprrypico-0a60df.local, MAC
88:a2:9e:0a:60:df. Refresh firmware revision/deployment match, boot, engine,
clock, output, owner/job, saved schedules/station/watermark, address and resources
before work. Require healthy storage, disabled schedules and authoritative
empty/inactive/unowned state before idle Console WIFI OFF/ON. Preserve boot and
saved state. No jobs, flash, restart, GPIO or RF are part of baseline diagnostics.
Existing explicit all-tests/USB/Wi-Fi/capture approval covers these scoped tests.

1. Inventory actual Mac and Linux interfaces, NSS order and Avahi state. Run
   network operations outside the sandbox. Distinguish privilege/tool-policy
   failures from LAN evidence. Keep native Mac dns-sd callbacks separately from
   automated Chrome navigation; manual Chrome navigation and in-page refresh
   were observed working with Anti-tracker enabled. Do not disable extensions or
   weaken origin/TLS protections to hide automation errors.
2. Audit previous recorder interference, especially the extra bound UDP 5353
   socket. Capture passively while testing NSS; any bounded seed query must close
   its socket before measuring resolver behavior. Preserve legacy-unicast versus
   native mDNS differences. No hosts edits, cache flushes or Avahi restarts.
3. Run three separately recorded orderly cases, each with 150 seconds off and
   up to 120 seconds for recovery followed by at least 30 seconds stable checks.
   Before disabling, require Mac positive observation, Linux NSS success and
   verified HTTPS. During loss record actual Pico A/PTR TTL-zero goodbye and
   native removal plus completed Linux negatives; timeout is not negative proof.
   Keep USB as the authority. Respect the one-second goodbye grace in RFC
   6762 section 10.1: measure required Linux negatives after that interval,
   including beyond the original 120-second TTL. After enabling, retain same-name probes/positive
   announcements and independently timed Mac/Linux resolution and authenticated
   reads. Do not equate local mDNS active with delivered advertisements.
4. Capture Pico-related mDNS plus separate bounded ARP/TCP/DHCP diagnostics on
   wspr5; sample USB counters/resource usage and peer state. If recovery fails,
   retain the first failure and observe a bounded diagnostic window before any
   further cycle. Compare direct-IP TCP/verified HTTPS, native resolution,
   packets, neighbor state and authoritative device state to locate the failing
   boundary. A finite passing series alone does not explain an old intermittent
   failure. Distinguish historical unknown cause from bounded repeatability.
5. Review lifecycle/resource code and repair evidenced defects only. If a target
   firmware repair is necessary, build and review the exact inhibited image and
   obtain any still-required image-specific flash approval before deployment.
   Run behavior-focused host checks and repeat affected physical observations.
   Never relax pass conditions to promote a retry or simulation into acceptance.
6. Bound and locally flush all observers; keep raw evidence/credentials private.
   Always restore Wi-Fi after authoritative idle reconciliation, close USB and
   captures, and verify installed service/provider unchanged. Do not delete or
   edit router entries. Report any incomplete cleanup explicitly.

Render results and a private artifact hash index. Adversarially assess real
identity/boot, Console/WTP operations, packet origin/TTL/PTR, captured versus
attempted goodbyes, native cache behavior, resolver timeouts, transport identity,
resource bounds, observer interference, hidden retries and exact cleanup. Fix
findings, rerun affected checks and perform a second assessment. Update the
joint matrix and development/review entry points with evidence-limited claims;
retain DHCP reassignment, two-board trust and overnight stability separately.
Review the staged changes, commit and push the requested Pico changes, verify
clean remote parity and report actual results plus remaining items.
