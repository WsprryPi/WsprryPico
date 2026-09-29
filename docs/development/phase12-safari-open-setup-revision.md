# Phase 12 Safari setup revision and execution brief

Status: **WI-FI-FIRST CONTRACT SELECTED; BOOTSEL BUTTON BEHAVIOR SELECTED;
SAFE IMPLEMENTATION AND TARGET ACCEPTANCE OPEN**
(last revised 2026-09-29). This decision supersedes the owner and physical-claim
portions of the earlier [P12.7 decision](phase12-7-decision.md). The earlier
design and failed physical claim attempts remain historical evidence.

The 2026-09-27 Wi-Fi-first correction below supersedes this document's original
single-screen wording. The filename is retained for existing links.

## 2026-09-29 BOOTSEL button decision

The operator selected these actions for the only onboard button, BOOTSEL:

- A short press stops any active transmission and restarts the application.
- A continuous press reaching ten seconds stops any active transmission and
  presents the setup SoftAP. Restart only if required to enter a safe working
  state. The long press must not also trigger the short-press restart.
- Neither action erases the Wi-Fi profile, station settings, schedules,
  watermarks or other journals. Reset and full erase remain distinct P12.11
  actions; this button decision does not silently select either erase action.

The device must request output shutdown as soon as a press is safely detected,
without waiting for the ten-second threshold. Classification occurs at release
for a short press or at the ten-second threshold for a long press. The output
must be confirmed inactive before either restart or SoftAP admission, including
an armed, running or autonomous job. The long-press AP action follows button
release because flash access must remain protected while BOOTSEL is held. An
unconfirmed output-off state is a failed action, not permission to open
setup or resume RF. A short press must not be acted on early in a way that
prevents recognition of the ten-second hold. The setup AP must remain available
long enough to perform a settings transaction while station Wi-Fi is healthy;
its exact lifetime and feedback are implementation decisions still to be
specified.

This selects the user-visible behavior, **not** the withdrawn background
sampler or a working firmware feature. BOOTSEL is tied to flash chip select:
holding it during power-up enters ROM USB boot mode before the application can
interpret a gesture. During runtime, an unprompted press can overlap flash
execution on either core. The
[long-hold incident and review](phase12-safari-open-setup-review.md) found that
the earlier sampler could resume flash execution while the button remained
held. A separately
[bounded prompted diagnostic](phase12-8-bootsel-window-target.md) survived one
press/release with both cores coordinated, but paused USB and network service
and did not demonstrate an always-available input or ten-second hold. The
[Raspberry Pi BOOTSEL example](https://github.com/raspberrypi/pico-examples/blob/master/picoboard/button/button.c)
also requires temporarily suspending flash access and warns about concurrent
flash users. No production image should advertise these button actions until
host fault tests cover shutdown and unknown-output paths, an exact RF-inhibited
target test proves arbitrary press timing, ten-second and stuck holds, both-core
flash use, AP recovery and reboot, and separately authorized conducted testing
proves actual transmission interruption. If the stock button cannot meet that
gate, the selected behavior needs a different physical or control input; it
must not be approximated by the removed short sampler.

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
