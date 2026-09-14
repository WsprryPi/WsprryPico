# Component 4: C7 LOAD reply investigation

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`, starting from
`495a647eaddef71e5970cff53ec6e335effecadb`. Investigate the C7 512-event LOAD reply
using local evidence and hardware-free tests.

Read the project instructions and current development guidance. Preserve
historical failures, protocol limits, the 32 KiB heap reserve, and existing
hardware qualification boundaries.

1. Extract the exact C7 LOAD request bytes from
   `build/phase11-5-r3-v2-capacity-c7/evidence/rf.jsonl`. Verify their identity
   against packet SHA-256
   `8cfcdfeef0c4513f24fe4dff64eaef1f62bbeaa4054c33d2d6720a3481e4b908`.
   Replay them through the production frame parser, request decoder, JobService,
   response encoder, and endpoint. Use a host RF adapter with the production
   frequency calculation where possible; clearly identify simulated behavior.
   Include the earlier retained job and replay state where evidence supports it.
2. Model captured TLS allocation and retained-memory costs. Account separately
   for input storage, decoded events, prepared-job storage, adjustment copies,
   replay records, reply pages, and reserve checks. Distinguish sampled target
   measurements from host allocations and modeled values. Identify which service
   refusal, encoder refusal, allocation failure, or endpoint closure is reproduced.
   Do not claim that a host reproduction proves the exact uninstrumented branch
   taken by C7.
3. Implement the smallest fix supported by that evidence. Preserve complete
   replies, idempotent replay, ownership, job limits, and memory reserves. Add a
   regression that fails on the previous implementation and passes with the fix.
   Test relevant low-memory boundaries, replay and retained-job behavior, partial
   allocation failures, and response framing.
4. Perform an adversarial review of the fix, tests, and conclusions. Repair
   actionable findings, rerun affected checks, and repeat the assessment until
   no actionable findings remain. Run relevant existing host tests and justified
   local build checks.
5. Save this prompt, reproducible fixtures or extraction procedure, memory
   analysis, test results, review findings, and remaining acceptance gates in the
   repository. Keep private captures, credentials, and generated binaries out of
   Git. Commit and push, independently verify remote parity, and report closure
   and remaining work.

This execution uses local files and host tests. It does not flash firmware,
control devices, or produce RF. Group 2 physical acceptance remains open until
separately authorized target evidence supports closure.
