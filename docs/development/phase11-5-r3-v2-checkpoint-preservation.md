# R3 v2 preservation and reuse rules

Each numbered validation checkpoint is append-only. Its individual assertions
retain their exact source, image, boot, configuration, workload and observation
scope. A failed later attempt cannot erase an earlier pass. A source or harness
repair requires an explicit impact assessment and only the affected checks;
physical observations keep their actual measured identity rather than being
relabeled as measurements of a later image. Historical failed attempts remain
available alongside corrected attempts.

Freeze raw archives, hashes, audit code and dependency closure, test logs,
results and any necessary executable/image before reusing a build directory.
Run evidence-mutation tests before awarding new physical assertions. Distinguish
product failures, harness failures and environment/permission failures from one
another. A component can pass while its enclosing attempt remains failed; name
both scopes and withhold any missing gate.

The integrity check after v2-009 found 103 matching direct artifact references
across v2-001 through v2-009. The two exceptions are v2-001's provisional
firmware ELF references in the mutable firmware output directory. Subsequent
builds replaced those files. The original build logs and frozen host binaries
remain available, but the original provisional ELFs cannot be claimed as retained
binary evidence. That checkpoint did not award physical image acceptance. New
image evidence is copied into dedicated immutable folders, including the actual
7d183978 deployed ELF/UF2 and the separate HTTP-padding provisional image. This
limitation does not invalidate unrelated host passes or later physical archives.

The private direct-reference integrity report is
`build/phase11-5-r3-v2-checkpoints/integrity-20260913-h1a.json`. It does not itself
reaudit every nested archive or promote any gate. The numbered checkpoints and
their frozen auditors remain the source for individual acceptance claims.
