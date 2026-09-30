# Pico setup pages

The firmware embeds these local pages and their bundles for the open Pico
setup AP. `/` and `/index.html` show Wi-Fi setup when it is available;
`/owner.html` shows the separate, optional station-settings flow. No external
scripts, fonts, analytics, or phone storage are required.

The Wi-Fi page shows the network and password fields immediately. A show/hide
control changes only the password field's visibility. The browser creates a
fresh encrypted WiFi-Bootstrap/1 submission for each save; the Pico checks the
candidate network before committing the next journal generation. The page
uses the exact request digest and generation to reconcile a lost response.
It also supports later network replacement without discarding a consumer
profile's station, TLS, or client material. The Pico restarts after a verified
save so the new profile loads from the journal.

The station page is a separate encrypted transaction. It sends an empty
network pair as a wire marker to use the Pico's saved Wi-Fi credentials;
firmware rejects that marker on a blank device. It does not expose or request
the saved Wi-Fi password. The existing TLS lifecycle still requires trusted
time, so a network with no usable time service cannot yet complete station
setup. The `owner` names in legacy wire and files do not grant persistent
phone authority.

Grid locators accept exactly four or six characters, for example `EM18` or
`EM18AA`. The page normalizes typed letters to uppercase; fields are A–R and
optional subsquare letters A–X. The full locator survives save and prefill.
The existing standalone Type 1 WSPR frame carries its first four characters.
Callsigns accept 3–12 uppercase letters/digits with nonempty prefix/suffix
segments separated by slashes, with at least one letter and one digit. The
full value survives save and prefill, including `AA0NT/P` or `PJ4/AA0NT`.
Extended callsigns are stored independently of transmission support: the
current automatic Type 1 encoder reports `UNSUPPORTED_MODE` and starts no job
for a callsign it cannot encode; it never drops an affix to transmit a base call.

Every fresh station page loads the saved callsign, grid and power from the
Pico's AP-local public status. This also works after a browser privacy refresh;
it uses no phone storage and does not issue Save. The status omits saved
Wi-Fi credentials and TLS/owner/client material. Polling can update an untouched
form when the committed generation changes; editing any field protects the
whole draft. Readback uses only a healthy matching device/generation snapshot,
so an old boot snapshot is not paired with a newly committed generation.

A captive sign-in window can perform setup if it has the required browser
cryptography. The fallback names a regular browser and the Pico URL, not a
specific browser brand. The same-origin and cryptography checks are functional
requirements; they are not a user-agent check.

After reading Pico identity/status, each page sends the browser's UTC once and
then about every 30 seconds while it remains open. No user action is needed.
The Pico treats this as a provisional browser hint with one second of
uncertainty. It cannot replace trusted SNTP/controller time, authorize a
scheduled job, or satisfy the fresh-SNTP requirement for TLS generation.
Opening the page is required; Wi-Fi association alone supplies no client UTC.

The locked dependencies are `@noble/curves`, `@noble/hashes`, and
`@noble/ciphers` 2.3.0, with upstream MIT licenses in [`licenses/`](licenses/).
The build uses pinned esbuild 0.28.2. Run `npm test` and `npm run build` in
this directory to validate and regenerate the checked-in bundles before a
firmware build. Browser and host tests do not replace an iPhone target test.
