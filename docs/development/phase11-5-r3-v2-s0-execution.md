# R3 v2 S0 staged finite RF admission

Reviewed under accepted R3-COMPLETE-20260913-v2; unchanged 60 dB conducted
wiring. Execute within that standing approval. A only, clean source 7d183978d08d,
boot 8e777dadaa81f4618154d84de0df268a, 138 MHz/divider 1/RAM/GP2, nominal
135.5 kHz. No flash, Wi-Fi cycle, CONFIG save or heap probe. B remains read-only.

E0a already independently passed the new image's idle maximum-input/job checks.
F0 is active with an independently armed deadline of host monotonic
290477130169000 ns. The runner checks the live timer and reserves its complete
240-second execution plus 150-second final observation/restoration interval.
It does not change or extend F0. A has joined 10.77.15.10 and a fresh inventory
shows synchronized normal-leap clock; fresh admission is required again.

Exactly two USB jobs, in order, each with positive LOAD and ARM acknowledgements:

1. Tone, 10 seconds at 135.5 kHz.
2. QRSS, 32 question marks, 384 events including a 1,000 ns off tail,
   143.250001 seconds total. Dot 0.25 s, dash/character gap 0.75 s,
   intra-character gap 0.25 s; six Morse elements per character.

The second job is real continuous message keying beyond both old duration and
event limits. It is an independent raw-event USB plan; it does not claim a
production Pi/browser compiler path or a one-hour maximum. Its pattern is
`..--..` repeated 32 times with explicit inter-character gaps.

Charge both starts prospectively before ARM; ambiguous ARM remains fully charged.
Total possible RF duration is 153.250001 seconds. Maximum eight 60-second lease
renewals. Preserve observed Loaded, Armed, Running, Complete and Empty transitions.
Only confirmed owned Complete with matching INFO epoch can be released.

Independent Console INFO requests every second (starts no more than two seconds
apart), WTP STATUS and host health every five (starts no more than six apart),
each reply within five seconds. STATUS is published before any next mutation.
Sole owner of each USB interface; no duplicate endpoint opens. INFO/health run
in separate threads. Listener-on baseline only; later packets add saturation.

Enforce unchanged 32,768-byte heap reserve, both guarded stacks, zero faults,
25 percent full/short predecessor reserves and the 2,849,391 ns service-gap bound.
A failed observer stops further job actions; surviving independent observers
continue through the original finite deadline. No blind mutation retry, flash
or inferred inactivity follows a disconnect. Final inventory must establish
A/B authority and retained configuration; unresolved state invokes separately
reviewed recovery within the already accepted completion scope.

Independent raw auditing must verify actual duration, launch/refill/tail/terminal
accounting and all observation cadence before awarding scoped credit. Passing
assertions are checkpointed; this smoke packet cannot close R3.

- `packet_sha256`: `966cd695df2b2eab36f6999c2afae678ad6eecdb8a3c5ea0871fb5afb2c61fef`
- `archive_sha256`: `5285d444817a0f13088f9eacd6f81faa81f4055fa6c58f7831f3fa137182e2a4`
- `runner_sha256`: `0a3fcc4c79be30bc3f77a68701b971c5892a3b0f98e1568e0d426ebff096dce9`
- `stager_sha256`: `399b4f5adfb75b6acdc14237e036eb96302ebdf5d0f7bb7f9c92165ca3a1a5d0`
- `root`: `/home/pi/phase11-5-r3-v2-smoke-s0-20260913`
