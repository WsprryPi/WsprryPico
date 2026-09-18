# Phase 11.5 Package 11 Retry 2 preflight review

## Scope and status

This review prepares the host tooling and bounded prompt for Retry 2. It does
not authorize or execute Retry 2, access a Pico, acquire the RF reservation or
add R6 acceptance credit. Phase 11.5 remains open at five of six families.

## First adversarial review

The first review of the credential-owner repair found two actionable issues:

1. the secure open rejected a symlink at the credential file but did not first
   reject symlinked parent directories; and
2. the final raw auditor required exactly one local fixture verification even
   though the reviewed setup can verify at setup and once more before launch.

The fixture now requires every credential parent to be a real directory before
opening a file, while retaining final-component `O_NOFOLLOW`, link-count,
regular-file, content-hash, owner and mode checks. The raw auditor now requires
one or more local verification records and checks every record against the
frozen remote BSSID. Focused tests cover file symlinks, directory symlinks,
content-hash changes and the required cleanup-armed / credential-protected /
radio-mutation ordering.

The review also found that a passed credential retest could become stale after
a fixture-source edit. Retry 2 staging now requires the retest's embedded
fixture source hash to equal the exact staged fixture input, and the campaign
validator binds the same equality.

The second source pass found that initial packet hashing still used ordinary
path reads. Staging now applies the same real-parent, single-link regular-file,
`O_NOFOLLOW` and open-inode checks before hashing any credential. Tests reject
both final-component and parent-directory symlinks in staging as well as at
runtime preparation.

## Reassessment

- The Linux host-only wspr5 retest passed against fixture source SHA-256
  `40a845e727a5b223c1e6428a8445df8b0d4ce1b9d0e28919cb883148ce2cbf92`.
  Six synthetic files changed from UID 1000 to UID/GID 0, remained mode
  `0600`, retained their hashes and caused no Pico, USB, network, service,
  reservation or RF action.
- Package 9 and Package 11 focused suites pass 31/31. The Package 11 suite has
  18 tests, including Retry 2 dependency/accounting rejection and credential
  applicability checks.
- The documented host build and CTest suite passes 81/81.
- The admission assessment rejects 26/26 mutations, the immutable Retry 1
  failure assessment rejects 31/31, and the synthetic final-closure assessment
  rejects 53/53. Each intact input validates again.
- Python syntax compilation and `git diff --check` pass.

No further in-scope tooling finding remains. The next action is the separately
authorized [Retry 2 prompt](phase11-5-package11-retry2-prompt.md), with a fresh
ceiling of 16 jobs / 356.8 planned RF seconds and a maximum cumulative Package
11 total of 32 jobs / 372.8 seconds after a complete run.
