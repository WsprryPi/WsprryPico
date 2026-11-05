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
reject compiler/wrapper overrides, all configure commands disable compiler
launchers, and each firmware configuration verifies that C, C++, and ASM use the
actual executables from the verified compiler archive with empty launchers.
No compiled-object or dependency cache is introduced. Dependency hashes,
submodules, image inspection, download inspection, and publication boundaries
remain independent.

## Current qualification and remaining work

All four affected local CTest contexts passed in 118.62 seconds, including the
actual network consumer, host interop, execution guards, and selected-source
regressions. Selected-source testing now changes a header without clearing or
reconfiguring its build directory and requires the changed marker from the real
consumer; missing source and actual compiler failure still refuse. All 68 bundle
methods passed, including four new methods covering freshness, preserved work,
compiler/wrapper refusal, and wrong shared-image contexts.

Current-pair recipes, same/different-source graph proof, incremental compiler/
asset/contract/image-definition checks, final normal/inhibited/reproducibility
checks, and actual canonical work counts are still pending. No reduction target
or completion is claimed before those gates pass.

## Documentation Impact

Updated the campaign result and changed-input inventory. The ordinary product,
protocol, installation, and operator controls are unchanged. Current CI/build
instructions will be consolidated in phase 10; no operator-manual change is
needed for these internal build boundaries.
