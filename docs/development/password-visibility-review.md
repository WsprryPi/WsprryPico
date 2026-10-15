# Password visibility — execution and adversarial review

2026-10-15. Executed the [implementation prompt](password-visibility-prompt.md)
on `devel`, starting from `ab7628dce1cee87e6433c020f22acf7c762561d6` with clean
tracked files. The unrelated untracked `tests/hardware/si5351-i2c/` is retained.

## Delivered behavior

The shared station/radio page uses the network setup page's existing eye/slash
artwork and right-side button treatment for local/saved-Wi-Fi login, ordinary
new Wi-Fi password and authenticated consumer Wi-Fi setup. The public setup
page keeps its existing layout and behavior. The shared SVG state defect found
below is corrected there too.

Each native button toggles only its own input, preserves the typed value and
selection and never submits a form or starts a network operation. All fields
start masked. Show/Hide accessible names, tooltips, pressed state and SVG slash
are synchronized. Inputs retain their identity, form name, autocomplete and
validation constraints, with capitalization and spellchecking disabled.
Buttons have a 44-pixel hit target, visible keyboard focus, explicit input
association and separate labels. Text has 56 pixels of trailing padding at the
normal font size. Disabled fieldsets and read-only consumer configuration stay
unavailable; no stored password is retrieved or displayed.

Submission masks the field. Login and consumer setup retain their existing
credential clearing on success/failure. Ordinary configuration failure retains
the correctable password draft while masking it; successful reload clears it.
Form reset re-masks; logout and page exit clear and re-mask all password drafts.
No secret is copied into labels, attributes, URLs, logs or persistent storage.

## Adversarial assessment and repair

Initial review checked native Enter/Space activation, form ownership, focus,
selection, maximum-length values, independent fields, disabled/read-only
behavior, async login/setup/configuration failure, reset/logout/page exit,
CSP, generated documents and mobile/text-size layout.

One actionable finding was reproduced visually: the original network setup
code assigned `.hidden` to an SVG path. That property does not reflect the SVG
`hidden` attribute, so passwords toggled correctly but the slash stayed hidden.
The copied initial control inherited that issue. Both implementations now use
`toggleAttribute('hidden', ...)`. Regression checks assert attribute state, and
native Chrome verifies actual DOM visibility on both the shared and reference
pages. No original artwork or workflow was replaced.

After this repair, affected checks and both firmware targets were rebuilt, the
native browser confirmation passed and the desktop/mobile confirmation images
were inspected. The final reassessment found no actionable issue in this scope.

## Validation

- `node tests/network_browser_tests.js`: PASS. Includes password independence,
  value/selection preservation, request-free toggling, read-only rejection,
  successful/rejected login clearing, logout/page exit and masked drafts after
  a failed configuration save, alongside existing ownership/failure checks.
- `npm --prefix src/network/bootstrap_web test`: all 11 tests PASS, including
  the existing setup eye and repaired SVG attribute checks.
- `npm --prefix src/network/bootstrap_web run build`: PASS; only the affected
  generated setup bundle changes. Other generated bundles are unchanged.
- `python3 scripts/generate_web_assets.py . build/password-visibility-assets.cpp`:
  PASS; embedded documents and CSP hashes generated normally.
- Retained host cache, after `source scripts/xcode_env.sh`: build PASS;
  `ctest --test-dir build/consumer-lan-host --output-on-failure -R
  'network_browser_tests|network_tests|bootstrap_http_tests|consumer_radio_tests|http_response_lifetime_tests'`:
  six affected checks PASS.
- `cmake --build build/consumer-lan-pico --target WsprryPico
  WsprryPico-StandaloneRF --parallel 4`: both retained-SDK targets PASS with
  linked-image safety/resource checks. No dependencies were downloaded or
  installed; the build log's picotool fetch wording resolves to the retained
  local tool.
- Chrome `155.0.8059.40`, local simulated API fixtures: actual generated station,
  consumer and reference setup documents run under their generated CSP.
  Pointer, native Enter/Space, no accidental submit/request, 63-character value
  and selection preservation, login rejection/success, setup/config failure,
  reset/logout/page exit and read-only behavior PASS. The actual consumer
  bundle executes; its application adapter is stubbed for this UI-only check.
  This is not new authentication, network or physical-device evidence.
- Desktop 1280 and mobile 390 CSS pixels inspected together, then confirmed
  after the SVG repair. Additional 320-pixel and 200% text-size checks have no
  horizontal overflow. Eye buttons remain 44 by 44 pixels, inside their input
  bounds, with a visible 3-pixel focus outline and no text overlap. The existing
  `#203a50` icon on white has contrast above 11:1.
- Impeccable detector run once: degraded regex mode because parser modules are
  absent. Its seven advisories concern pre-existing stylesheet/design-record
  mismatches; none is introduced by these controls. It does not establish
  contrast or parser-based accessibility coverage. Native checks supplement it.
- `git diff --check`: PASS.

Private, ignored evidence: `build/password-visibility-browser-confirmed/`,
`build/password-visibility-browser.mjs`, `build/password-visibility-host-tests.log`
and `build/password-visibility-final-build.log`. Earlier fixture failures are
retained separately: the CDP harness initially omitted keypress text and did not
scroll an offscreen logout button into view. Those were fixture defects, fixed
before the accepted run; they did not cause Pico or configuration changes.

Neither Pico was contacted, flashed or reconfigured for this slice; there was
no RF job. No firmware was installed as part of this slice. A device shows this UI
change after firmware containing this commit is installed. Native Safari/iOS/Android and assistive-technology user sessions were
not performed. Authentication, protocols, persistence, scheduling and RF
implementation remain unchanged.
