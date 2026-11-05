# Phase 02 enforcement change

Current readback on 2026-11-05: devel protection explicitly returns “Branch not
protected” (404), and applicable repository rules are an empty list. This is an
explicit absence response, not an authentication failure. The existing required
software job is `verify`, produced by GitHub Actions (application 15368).
`publish` is optional and stays outside the required check set.

Apply only to WsprryPico devel: require `verify` from application 15368 on the
current up-to-date merge candidate; require pull-request merging; no review-count
requirement, no force push, no deletion, no bypass actors, and administrator
enforcement. No publication settings change. This means direct pushes and
skip-CI documentation candidates cannot merge until a current verification check
has run. Existing draft PRs remain editable; opening or updating them runs the
unchanged verification workflow. Main and unrelated repositories are untouched.

The session standing execution authority authorizes this prepared application.
Recovery for an unavailable verifier is to restore the workflow through a tested
PR and rerun it. Weakening or bypassing the gate is outside this campaign.
Capture the applied remote readback and hosted result before claiming this gate
active. Execution evidence uses an independently versioned sidecar selected from
the frozen producer; retained older deployment manifests remain readable.
