# Phase 12 Safari setup revision and execution brief

Status: **WI-FI-FIRST CONTRACT SELECTED; GP14 BUTTON TIMING SELECTED;
PRODUCTION IMPLEMENTATION AND TARGET ACCEPTANCE OPEN**
(last revised 2026-09-29). This decision supersedes the owner and physical-claim
portions of the earlier [P12.7 decision](phase12-7-decision.md). The earlier
design and failed physical claim attempts remain historical evidence.

The 2026-09-27 Wi-Fi-first correction below supersedes this document's original
single-screen wording. The filename is retained for existing links.

## 2026-09-29 GP14 button decision

The operator selected a separate active-low button on **GP14, Pico 2 W physical
pin 19**. A normally open switch to ground, or a test jumper to ground, is the
intended input. The internal pull-up holds the unpressed level high. This
supersedes the release-only BOOTSEL timing below, while preserving the BOOTSEL
failure as historical evidence.

- A debounced press released before 0.4 seconds requests a device reset. This
  is a restart, not a settings erase.
- A press released from 0.4 to less than 0.9 seconds requests transmission
  shutdown on release.
- At 0.9 seconds of continuous hold, request an immediate stop of active and
  autonomous transmissions; release is not required.
- At 9 seconds of the same hold, request setup SoftAP. AP admission must wait
  for confirmed RF shutdown. If shutdown is not confirmed, the AP request
  fails closed.
- Each threshold acts once per press. Keeping a jumper on GP14 past 10 seconds
  must neither repeat either action nor withdraw or impair an opened SoftAP.
  The next gesture is armed only after a debounced release. A low input already
  present at boot is ignored until release, preventing a reset or AP loop.

The shutdown path must cover the autonomous scheduler, `JobService` and the
physical engine, including an armed or running job. No gesture erases the
Wi-Fi profile, station settings, schedules, watermarks or journals. Reset and
full erase remain distinct P12.11 decisions. The current
`src/provisioning/button_control.hpp` still records the older disconnected
release-only policy; it is not an adapter for the selected GP14 behavior.
The separate [GP14 diagnostic](phase12-gp14-button-diagnostic.md) evaluates
input timing and both-core flash continuity but performs no reset, RF stop or
SoftAP action. A later [opt-in runtime source candidate](phase12-gp14-runtime-review.md)
connects PIO capture, normal reset and the existing SoftAP coordinator in an
RF-inhibited image. The default image does not advertise GP14, and real RF
shutdown, integrated AP operation and physical timing remain unaccepted.

The [arbitrary BOOTSEL feasibility gate](phase12-bootsel-arbitrary-press-feasibility.md)
found no safe way to capture an unprompted BOOTSEL press while both cores may
access XIP flash. The stock switch is tied to flash chip select. The
[long-hold incident](phase12-safari-open-setup-review.md) and the
[prompted-window result](phase12-8-bootsel-window-target.md) remain bounded
evidence, not GP14 acceptance. Production needs host fault tests, an exact
RF-inhibited GP14 physical test for arbitrary presses and stuck holds, AP
recovery after confirmed shutdown, then separately authorized conducted RF
testing of actual transmission interruption.

## 2026-09-28 BOOTSEL long-hold correction

After the reported physical 11-second BOOTSEL attempt, Candidate A's application
USB serial was absent, its previous station address did not answer, and an
RP2350 USB bootloader was present on the Pi. A later serial-targeted ROM read
bound that bootloader to Candidate A. The background sampler
could return to flash execution while the button remained held; this is an
unsafe implementation of the selected manual AP gesture. The source
removes that sampler and the USB single-sample probe. Do not use a runtime
BOOTSEL hold on the flashed image. Automatic AP startup for a blank profile
and station-loss fallback remain selected. Opening an AP while station Wi-Fi
is healthy needs a new, physically safe action and target acceptance before
this contract can be considered complete.

## 2026-09-28 SoftAP lifetime correction (manual gesture superseded)

The open AP starts immediately when the profile journal has no saved Wi-Fi
credentials. With a saved network and a usable station address, it is normally
off. If the saved station is unusable for 60 seconds, the AP returns so the
same Wi-Fi-first page can replace settings at a field site. Once station Wi-Fi
has been stable for 30 seconds and no setup transaction or reply needs the AP,
it withdraws. The previously selected background BOOTSEL opener was superseded
by the correction above; the 2026-09-29 button behavior is a later selected
requirement with safe implementation still open. A two-short-flash LED pattern
every two seconds marks an available AP; the three-flash Identify pattern remains
distinct. Saving on the page still has no button step. Neither production
image samples BOOTSEL at runtime.

The captive DNS responder maps ordinary A queries to `192.168.4.1`, and the
HTTP service redirects foreign hosts to the local setup root. The automatic
sign-in window depends on the phone; `http://192.168.4.1/` remains the browser
fallback. A repeated save of the same connected network reuses the existing
station link, commits a distinct request result, and reports verified success.
A changed network stops the prior station before the trial and restores it on
failure. A lost result with no exact journal match is reported as unverified,
not as a confirmed failure.

## Wi-Fi-first correction

The captive landing page at `http://192.168.4.1/` shows the Wi-Fi network and
password fields immediately, with a show/hide eye control. **Connect to Wi-Fi**
encrypts and saves only the network details; no BOOTSEL press, code, owner key,
or station setting is needed. The Pico verifies association and an IP address,
commits the next journal generation, reports the exact request result, and
restarts after the result is delivered or after a bounded fallback. The same
page may replace Wi-Fi on a network-only or consumer profile; a failed join
restores the previous network.

Station details are on the separate `/owner.html` page and are optional later.
Its encrypted transaction uses the current saved network credentials inside
the Pico, without showing or asking for the Wi-Fi password again. It cannot
save before Wi-Fi setup. A station save still requires a usable time source
for the current TLS lifecycle. A successful station save preserves the stored
Wi-Fi configuration. The internal `owner` wire name remains legacy terminology;
no phone retains owner authority.

The captive sign-in window may run setup when it supports the required browser
cryptography. If it cannot, the page asks the user to open the Pico address in
a regular browser; Safari is one option, not a required product step. The
source checks browser capability and the exact Pico origin, not a Safari user
agent. Physical iPhone acceptance of this revised flow remains open.

Both local pages send the browser's UTC when opened and about every 30 seconds
while open. The Pico may use that lower-confidence hint while it lacks a
trusted source, and fresh SNTP or authenticated controller time supersedes it.
The browser hint has one second of uncertainty, so it cannot authorize a
scheduled job or satisfy the fresh-SNTP gate for TLS credential generation.
Merely joining the SoftAP does not transfer time; the portal must load.

## Consumer contract

Opening the Pico's open setup AP launches the captive page when iOS permits;
`http://192.168.4.1/` is the browser fallback. The sole ordinary password entry is the destination
Wi-Fi password. A **Blink Pico LED** button is optional and shows three short
flashes for about ten seconds on the later station page. Each save starts one
encrypted transaction and reports checking, verified save, or a
retryable failure. Setup asks for no code, AP password, owner key, certificate,
USB command or BOOTSEL press.

The browser creates fresh P-256 and X25519 material for each save and retains
no phone credential. A different phone can open the same page and replace
Wi-Fi and station settings on an already configured Pico. The profile records
owner epoch zero and an empty owners list. The P-256 point in the existing
claim transcript binds only that request; the `owner` names in the wire and
source are legacy internal names, not user-facing authority. The operator
explicitly accepts open-AP active page replacement and relay risk for this
code-free, button-free local flow. No ordinary setup path grants RF authority.

The open setup AP returns when a saved network cannot be joined at a field
site. The local page and
status must load without station association. A save
still requires the candidate station network to associate and receive an IP
address. The current full consumer commit also requires fresh trustworthy
SNTP time to generate or validate TLS material. A field network without time
service is therefore a remaining functional gap for changing settings there;
the portal's availability alone does not close that row.

## Historical comprehensive execution prompt

This section records the earlier single-screen implementation brief. The
Wi-Fi-first correction above is the current UI and transaction contract.

Work in `devel`. Preserve unrelated changes and all hardware evidence.
Implement the contract above in the existing captive HTTP, claim slot,
browser and profile journal paths. Serve the same immediate form from `/`,
`/owner.html` and the older `/index.html` alias whenever setup is available.
Disable the older BOOTSEL-gated network-only mutation in the consumer image.
Keep the public status identity-bound, reject malformed or foreign AP requests,
use one-use encrypted submissions, preserve transactional journal activation
and old network fallback on a failed replacement. Allow source-5 consumer
profiles to be updated by a different phone and retain valid device TLS and
station clients across such a settings change. Report a retained owner only
when one is actually stored. Keep Wi-Fi secrets out of browser storage and
diagnostics. Verify page-state recovery after transport loss and avoid claiming
a save until the exact request digest and generation are read back.

Run browser and C++ host tests, regenerate the embedded web assets and cross
build Pico 2 W. Review the code adversarially for wrong-profile writes,
stale transactions, credential exposure, AP/STA loss, save-result ambiguity,
and source-5 authority leaks. Repair findings and reassess. Record exact
source versus target evidence. Commit and push the reviewed source. Flashing,
USB control and RF tests remain separate action-specific hardware steps under
`AGENTS.md`; a source build or push does not authorize them.

## Acceptance still required

- One new-image iPhone test: the Wi-Fi-only form opens immediately, the eye
  control works, and a save reaches exact generation/readback without a button.
- Separately open station settings later, confirm no Wi-Fi password is requested,
  and verify the station transaction retains the saved network.
- Reboot, field-site station-loss and different-phone update tests with the
  same page; include a failed join followed by retry and old-profile recovery.
- Decide and implement an offline-time path if a field network lacks SNTP.
- Complete the remaining Phase 12 target, resource, trust and restoration
  rows in the [roadmap](phase12-plan.md). Source tests cannot close them.

The [source review](phase12-safari-open-setup-review.md) records the executed
checks, repairs, second assessment and open target gates.
