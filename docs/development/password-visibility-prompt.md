# Password visibility controls — implementation prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Implement the request,
perform an adversarial review, fix every actionable finding and reassess,
then commit only this slice, push `origin/devel` and independently verify the
remote SHA. Preserve unrelated work, especially `tests/hardware/si5351-i2c/`.
Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md and the documented
validation commands before editing. Inspect current status and history first.

## Selected requirement and reference

The user needs an eye control to inspect the password they are typing. It must
look and behave like the existing Wi-Fi password control on network setup
(`src/network/bootstrap_web/index.html`, `style.css` and `app.js`). Preserve that
reference's eye/slash artwork, right-side placement and explicit click-to-toggle
behavior. Keep the incumbent station-control design; no redesign, new library,
font, external icon request or new network/API operation is needed.

## Implementation scope

Add the control to the shared station/radio page's local/saved-Wi-Fi login,
new Wi-Fi password in the ordinary configuration form, and Wi-Fi password in
the authenticated consumer network-setup form. This page serves consumer LAN,
consumer AP and engineering access; share one small implementation across its
fields. Preserve the public network-setup control and repair any demonstrated
shared visibility-state defect without changing its appearance or flow.

- Passwords start masked. A native `type="button"` eye reveals only its associated
  input; a second activation masks it. Preserve the value, field identity,
  name, autocomplete, min/max length, required constraints and form semantics.
- Reuse the existing inline SVG eye and slash; use currentColor and hide the SVG
  from assistive technology. Provide an accurate Show/Hide accessible name,
  matching tooltip, pressed state and explicit association with the input.
- Support pointer/touch and native keyboard activation, visible focus, logical
  tab order and a minimum 44-by-44 CSS-pixel target. Keep the button outside the
  input's label and reserve enough field padding to prevent text/icon overlap.
- Preserve editing and caret/selection on the same input. Prevent automatic
  capitalization/spellchecking of revealed secrets. Remain usable with long
  passwords, narrow screens and zoom; do not introduce horizontal overflow.
- Independent fields must not affect each other or submit their forms. Respect
  disabled fieldsets and read-only fields; a read-only consumer configuration
  password must not appear to reveal a saved secret. Saved passwords remain
  unavailable to the browser and are never fetched or inserted by this feature.
- Re-mask when a credential is submitted or its value is cleared/reloaded.
  Reset the icon/label/state together. Preserve existing clearing on login and
  consumer setup, and preserve correctable configuration drafts on failure.
  Clear and re-mask password drafts on logout/page exit and honor form reset.
- No password may enter labels, status text, HTML attributes, URLs, logs, browser
  storage or evidence. Toggling must be a local presentation change only.
- Preserve CSP, authentication, encryption, transactional setup, settings,
  schedules, cursor, JobService and RF behavior. Keep assets compatible with
  both generated station and consumer documents.

## Validation and review

Use focused deterministic browser behavior checks and a real installed browser
with local simulated API fixtures. Cover default/two-way state, exact value and
selection preservation, independent fields, Enter/Space activation, no accidental
submit/request, disabled/read-only behavior, reset, success/failure clearing,
logout/page exit and maximum-length input. Exercise the actual generated
station and consumer documents with their CSP, and verify the reference setup
control still works. Batch desktop and mobile screenshots, inspect once, repair
any demonstrated issue and confirm at most once more.

Run the affected documented checks, asset generation and both retained-SDK Pico
builds as needed to validate embedded assets, without downloading dependencies.
This is a UI-only slice: no RF experiment, network/profile replacement, physical
button interaction or Pico A change is needed. Use no hardware mutation for
validation; report that no Pico firmware was installed as part of this slice.

Assess accessibility, secret handling, form ownership, async failure paths,
read-only/disabled state, layout, CSP and generated assets adversarially. Repair
findings, rerun affected checks and reassess until none remains in this scope.
Record results and limitations in the repository, review the complete diff,
stage only intended files, commit on `devel`, push and compare `git ls-remote`
with local HEAD. Report the prompt/results paths, user-visible behavior, checks,
review outcome, actual board/deployment state, commit and remote parity.
