# R3 v2 HTTP maximum-body admission correction

Source review found a concrete admission defect before attempting HTTP-MAX on
hardware. BrowserApi::handle reserved twice the complete HTTP body size plus
16 KiB working space and the unchanged 32 KiB recovery reserve. The parser
already owns that complete body. A valid HELLO padded to 32,768 bytes with
outer JSON whitespace therefore demanded 114,688 additional free bytes, even
though its internal envelope and decoded fields remain small. The envelope
also reserved the original body size despite omitting that outer whitespace.

A deterministic regression injects 90,000 available bytes after HTTP body
ownership and requires this harmless request to succeed without changing the
Empty service state. The original source fails that assertion. This proves an
admission-estimation defect, not target allocation exhaustion or a physical RF
failure. Existing exact-body tests with whitespace inside the operation body
remain distinct: that whitespace still belongs to the internal envelope.

The correction estimates extra working space from the body after excluding
only outer JSON whitespace, and reserves the envelope using the actual raw
fields it copies. It preserves the original bytes, request digest behavior,
HTTP 32,768-byte and WTP 65,536-byte limits, message/event/duration limits and
32,768-byte recovery reserve. Meaningful payload and whitespace inside strings
or nested bodies still count. Exhaustion still returns a bounded 503 response.
Physical HTTP-MAX and its under-RF resource assertions remain unvalidated until
a fresh identified image is built, admitted and exercised.

The first local reproduction command selected the old build-host directory,
whose private test certificates had expired. Its build failed before compiling
the new test; a subsequently invoked old test executable was stale and receives
no validation credit. Both logs are preserved. The actual current campaign
build is build/phase11-5-r3-diagnostic-host, as recorded in checkpoint v2-002.
The repeated command used checked subprocess dependencies, compiled the new
regression and reproduced the expected assertion failure. This separates an
agent build-directory mistake from the independently reproduced source defect.

Private logs:

- /tmp/r3-http-padding-before-build.log and before-test.log: rejected stale-build attempt.
- /tmp/r3-http-padding-reproduction-build.log and reproduction-test.log: genuine regression reproduction.
- /tmp/r3-http-padding-fixed-build.log and fixed-tests.log: affected repair validation.

## Evidence impact to verify before final acceptance

H0/H1a/H2b submit complete jobs over USB and use only GET requests through this
HTTP entry point. Their original source/image/boot remain recorded exactly;
no source edit changes their running device. Preserve independently validated
mode-hour, local execution, native WTP and terminal-TTL assertions. Do not relabel
old-image measurements as new-image measurements.

Before applying those assertions to final acceptance, compare RF renderer and
worker source/object identity, fixed buffers, RAM placement, heap and stack
boundaries, and the unchanged USB/WTP job path. The new image must receive idle
admission plus affected physical HTTP/browser/contention checks and resource
observations. Reopen any assertion whose dependency changes. The source/layout
comparison and final-image physical checks are still required; this document
is not yet a completed equivalence assessment.

## Repair validation and provisional image comparison

The corrected API and adapter tests pass. The real TLS suite first could not
start its loopback listener inside the filesystem/tool sandbox; the same rebuilt
binary passed all TLS checks once given its required local socket permission.
That startup failure is an environment result, not a firmware regression.
Checkpoint v2-008 preserves the exact source patch, logs and provisional images.

Both firmware targets cross-link. The provisional RF renderer remains at
0x200012d8, 660 bytes, with byte-identical machine code. Eighty-six RAM functions
are byte-identical at the same addresses; forty-two checked heap/stack/static
RF/application symbols have unchanged sizes and addresses. Other RAM code/data
contains relocated flash references, including USB and unwind veneers, so this
is not a whole-image binary-equivalence claim. The build recompiled only
src/network/api.cpp; RF source and fixed buffers are unchanged. Repeat the
comparison against the final clean identified image, then run affected physical
HTTP/browser/contention checks before accepting reuse.

Current host build: build/phase11-5-r3-diagnostic-host. Hardware-free TLS tests
require permission to bind their local loopback listener. Build and test commands
are dependent: use checked subprocess calls so a failed build cannot execute a
stale binary and create a false pass.
