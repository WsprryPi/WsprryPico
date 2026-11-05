# Phase 08 build consolidation

The candidate is prepared; final build, invalidation, source-pair, and canonical
acceptance gates below remain pending.

## Graph and reuse boundaries

The selected host-client consumers previously compiled five identical source
paths twice. Their warning flags differed. The shared host-only object target
now uses the stricter -Wall/-Wextra/-Wpedantic/-Werror context, with independent
objects for different physical source roots. Both buildable static archives,
consumer targets, source verifiers, includes, and C++20 remain. No firmware or
independent reproducibility build links this host-only target. A local build
actually compiled five objects and linked both archives and actual consumers.

Prechange object inspection found four full-object differences; removing debug
data reconciled three, while JSON emitted code still differed. No old object is
reused on the strength of matching filenames or byte hashes. The current shared
objects are freshly compiled under the common stricter context and require
production-path qualification.

The normal and inhibited recipes supplied identical configure options except
for their build-directory path. Independent phase 07 audit comparison found
all 2,368 declared compilation entries equal after normalizing only that directory.
The graph already declares distinct targets, image definitions, metadata, engine
wiring, generated inputs, linker reservations, and post-link checks. The candidate
builds both targets in the first fresh configuration, sharing only the common
objects CMake already owns. It checks that the accepted normal ELF, map, and UF2
remain byte-identical after building the inhibited target. Each image retains
its own audit material and every linked-image check. Declared entries are not
claimed as executed compilation counts; the earlier 175-object overlap remains
a ceiling until actual candidate logs are reconciled.

The second normal reproducibility build remains in a separate fresh directory.
An overlooked pre-existing reproducibility directory now refuses explicitly,
including a broken symlink, without modifying existing work. Canonical inputs
reject compiler/wrapper overrides, all configure commands disable supported C/C++ compiler launchers, and each
firmware configuration verifies C, C++, and ASM compiler selection plus the first
executable in every declared compiler command against the verified archive.
Target properties can override launcher cache defaults; cache values alone were
not accepted as proof. The direct-command reader uses the existing 64-MiB audit
limit for the actual 27-MB inventory and memoizes repeated executable resolution.
No compiled-object or dependency cache is introduced. Dependency hashes,
submodules, image inspection, download inspection, and publication boundaries
remain independent.

## Current qualification and remaining work

All four affected local CTest contexts passed in 118.62 seconds, including the
actual network consumer, host interop, execution guards, and selected-source
regressions. Selected-source testing now changes a header without clearing or
reconfiguring its build directory and requires the changed marker from the real
consumer; missing source and actual compiler failure still refuse. All 68 bundle methods passed, including four new methods covering freshness,
preserved work, compiler/wrapper refusal, and wrong shared-image contexts.

The same/different-source probe used the actual selected-client CMake function,
real Pi sources, and two executable consumers. One selected peer compiled five
objects for both archives. A header edit without reconfiguration compiled one
object and updated both consumers; a compiler-input change compiled all five.
Selecting a second physical peer compiled its own five objects and executed its
distinct marker. Missing source and a genuine compiler error refused rather than
using an existing archive or another peer; restoration passed without clearing
the build. Outputs are build/campaign-phase08-host-graph/proof.json and its
per-command receipts/logs.

Adversarial inspection found two additional proof gaps and closed them:

- An injected wrapper in a real 2,368-entry canonical command inventory passed
  the former cache-only check and failed the new command check. CMake initializes
  target launcher properties from cache values, which is not proof that they
  remain equal; see the [CMake launcher contract](https://cmake.org/cmake/help/v3.31/prop_tgt/LANG_COMPILER_LAUNCHER.html).
  ASM has no such launcher property, so direct assembly command inspection is
  required. No unsupported ASM launcher option is passed.
- The former direct build accepted a real generated config/update limit of 2047
  bytes while the authoritative schema still required 2048. Ordinary CI already
  checked generated files through CTest; incremental configuration lacked that
  gate. Configure dependencies now include the generator, its schemas, and all
  four outputs, and configuration checks exact current generated content. The
  same uncleared build refused the wrong limit before compilation, then rebuilt
  the actual core successfully after restoring 2048. A new permanent one-case
  regression passed in 0.871 seconds and independently checks the source limit,
  observed input timestamp change, intended refusal, and restored configuration.
  It never uses a synchronization sleep.

Local normal and inhibited builds passed all linked-image checks using the
private, fully initialized pinned SDK copy and the existing Arm GNU 15.3.1
compiler. The normal ELF, map, and UF2 remained byte-identical after the inhibited
build. Captured normal-stage logs contain 641 compiler and 14 link invocations;
the additional inhibited stage contains 390 compiler and one link invocation.
The separate phase 07 inhibited stage contained 565 and 12 respectively. These
are actual stage-log counts including nested tool builds, not merely declared
entries. Full candidate canonical reconciliation is still required before
claiming cumulative savings. Main-graph .ninja_log counts (547/6 then 390/1) are
separately recorded and must not be mixed with stage-log totals.

The first candidate 7d139c82cd9e1f6824c32f78cefe2b8e2fa827ee passed both
production source-pair suites; later validation-only edits are disclosed above.
Its canonical run 42105319549 was intentionally cancelled when superseded by
the stronger compiler and generated-input guards. This is not a successful
required run or an intermittent-failure rerun. Final acceptance requires the
revised intended candidate. Source-pair logs will retain distinct names.

Final current-pair recipes, incremental asset/image-definition sensitivity,
final normal/inhibited/reproducibility checks, and actual canonical work counts
are still pending. The changed-input manifest charges nine executable/configuration
paths, two new files, five new methods, one CTest registration, and 248 net
physical lines. The existing source-selection regression adds one incremental
client compilation and two links per run. No unused-file deletion receives
savings credit. No reduction target
or completion is claimed before those gates pass.

## Documentation Impact

Updated the campaign result and changed-input inventory. The ordinary product,
protocol, installation, and operator controls are unchanged. Current CI/build
instructions will be consolidated in phase 10; no operator-manual change is
needed for these internal build boundaries.
