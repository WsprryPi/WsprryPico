---
name: WsprryPico Station Control
description: Source-derived conventions for the embedded station control interface.
colors:
  header-navy: "#263e52"
  modal-backdrop: "#132331"
  action-blue: "#225e8a"
  canvas: "#f6f7f8"
  field-surface: "white"
  body-text: "#25313d"
  action-text: "#203a50"
  help-text: "#52616e"
  section-border: "#c8d1d9"
  field-border: "#687e90"
  button-border: "#687e90"
  focus-amber: "#b37617"
  busy-backdrop: "rgb(15 28 40 / 48%)"
  busy-dark-surface: "#243746"
  busy-dark-border: "#96adbd"
  busy-dark-backdrop: "rgb(0 8 16 / 62%)"
  notice-surface: "#e7eef4"
  notice-border: "#b6c6d3"
  error-surface: "#fff0ed"
  error-border: "#bd6755"
  error-text: "#882b19"
typography:
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  page-title:
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.2
  section-heading:
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.5
  status-value:
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  status-label:
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
  status-heading:
    fontSize: "1.65rem"
    fontWeight: 700
    lineHeight: 1.25
  status-heading-narrow:
    fontSize: "1.4rem"
    fontWeight: 700
    lineHeight: 1.25
  comparison-heading:
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.5
  label:
    fontSize: "1rem"
    fontWeight: 600
  help:
    fontSize: "0.875rem"
    fontWeight: 400
rounded:
  control: "4px"
spacing:
  field-gap: "1rem"
  section-gap: "1.5rem"
  page-inset: "1.25rem"
components:
  button-primary:
    backgroundColor: "{colors.action-blue}"
    textColor: "{colors.field-surface}"
    rounded: "{rounded.control}"
    padding: "0.5rem 0.9rem"
  button-secondary:
    backgroundColor: "{colors.field-surface}"
    textColor: "{colors.action-text}"
    rounded: "{rounded.control}"
    padding: "0.5rem 0.9rem"
  input:
    backgroundColor: "{colors.field-surface}"
    textColor: "{colors.body-text}"
    rounded: "{rounded.control}"
    padding: "0.6rem"
  notice:
    backgroundColor: "{colors.notice-surface}"
    rounded: "{rounded.control}"
    padding: "0.8rem 1rem"
---

# Design System: WsprryPico Station Control

## Overview

This record applies to the admitted operator pages in `src/network/web/` and the Wi-Fi-first, optional station and recovery pages in `src/network/bootstrap_web/`.
It records the embedded operator interface's native controls, feedback and
recovery conventions. No new brand metaphor, visual identity, or approved composition is
established. WsprryPi has its own design record; its fonts, Bootstrap components,
and theme rules are not dependencies of this embedded surface.

The interface presents station state and editable forms in a centered light
page beneath a navy header. Technical values, plain labels, inline help, and
explicit recovery messages carry the hierarchy. Timing belongs to the Pico;
the browser prepares complete jobs and reports observations.

**Key Characteristics:**

- Flat sections separated by borders and spacing.
- Native controls with visible keyboard focus and explicit labels.
- Inline validation that preserves the entered draft.
- Exact finite-job duration and numerical event capacity.
- Confirmed status remains separate from estimated progress.

## Colors

The navy header establishes application identity. Action blue marks primary
buttons and the text caret; white fields sit on the light neutral canvas.
Body and help text use separate dark neutral values. Borders distinguish fields,
buttons, and section boundaries without decorative fills.

Amber marks keyboard focus. Errors use explanatory text as well as the error
foreground; the global notice also gains an error surface and border.
Color alone does not express validation or RF output state.

## Typography

Body text and controls use the system stack recorded above, with controls inheriting the surrounding font. Form labels and default definition values are semibold; saved-setting comparisons and Transmitter status use regular-weight values. Help text is smaller and normal weight. Every definition value in Transmitter status uses the same status-value role: one system family at 1rem, regular weight 400 and line height 1.5, including accepted-job details, the next transmission, RF correction and device state. The status-label role uses smaller, muted, regular-weight text to distinguish labels from values; multiline details retain line breaks and wrap within their column. All peer operator disclosure labels use the section-heading role, including semantic headings nested inside summary and About this Pico / Diagnostics. Their family, size, semibold weight and line height stay identical in locked, unlocked, narrow and zoomed views. Page and active-status headings retain their distinct hierarchy. No additional font assets are loaded.

Message previews and progress use tabular numerals. Keep units attached to
values and retain significant subsecond digits; do not round away a finite-job
limit violation. Paragraphs have a maximum width of `75ch`.

## Layout

The page and footer share a `960px` maximum width and `1.25rem` side inset.
Main content starts with `2rem` top padding. Sections have `1.75rem` vertical
padding, a one-pixel top divider, and `1.5rem` preceding margin.

Fields use three equal columns with `1rem` gaps. Status values use three equal
columns with `1.5rem` gaps; long values wrap. At `650px` and below, fields become
one column, status values use two columns, device identity becomes one column,
and header content stacks. Main top padding becomes `1.5rem`. Buttons retain
content-based width, a `44px` minimum height, and a full-container maximum width.

## Elevation & Depth

The stylesheet uses no box shadows. Spacing, one-pixel borders, white controls,
and the notice tint distinguish structure and state. Keep this existing flat
section treatment when extending these forms.

## Shapes

Fields, buttons, and notices share compact `4px` corners. Sections are open
page regions rather than cards. Native checkboxes and disclosure markers retain
their recognizable control geometry.

## Components

### Buttons and navigation

Primary buttons submit settings or load and arm a complete job. Secondary
buttons use white surfaces with dark text and a one-pixel border. Enabled hover uses `brightness(.93)`; disabled buttons retain `.6` opacity. Locked settings wrappers and their nested fieldsets retain full opacity so disclosure labels and read-only content remain legible; native disabled controls continue to enforce access.
Keyboard focus has a three-pixel amber outline with a three-pixel offset. Programmatic section targets retain a one-rem scroll margin so the outline stays visible.
The navy header contains the home link and two view links, Station Control and Wi-Fi/Host. Active navigation uses a 3px underline and aria-current. Selecting a view scrolls to window top while retaining the document, session and drafts. Native section summaries replace the body menu. Top closes managed and nested disclosures and focuses the hostname. Station starts with merged Transmitter status; Saved settings and recovery sits immediately above the final About this Pico / Diagnostics section. Wi-Fi/Host contains network, Pico password, hostname and Logging. WSPR Configuration and Radio pins have separate save/apply ownership; one cannot apply the other's drafts.

### Device identity

The device presentation uses the boot-active hostname as the one main heading in shared chrome,
above both task areas. Product and task labels stay unchanged. The heading and
tab title share one observation controller. Fresh names need no helper line. Diagnostics identifies public versus authenticated observation. A saved rename appears secondarily
as pending restart, and connection/session loss labels the retained name last
confirmed. With no usable observation, show hostname unavailable and current-IP/
setup-Wi-Fi guidance. Discovery/reachability remains separate from the name.

The native About this Pico / Diagnostics disclosure stays outside area hiding.
Its full stable device ID and separately labelled observed boot ID use selectable
text. Long names and IDs wrap; no clipboard API, focus change, live region or
extra request is attached to opening it. Login status describes authentication
and does not repeat the stable ID. Deliberate retirement/target confirmations
retain exact IDs. No new brand, palette, typography or commissioning UI is added.

### Inputs and disclosures

Labels sit above full-width fields. Help is separate from the accessible field name and is associated with its control through `aria-describedby`. Grouped validation associates the error with every affected control and clears stale invalid state when a group member changes. Help stays beside its field and identifies
units, bounds, and consequences. Native `details`/`summary` disclose timing
settings and job-file loading; summaries have a `44px` minimum height. Focus
styling applies to inputs, textareas, selects, summaries, buttons, and links.
Disabled fieldsets reflect connectivity, ownership, and capability availability.

**The Preserved Draft Rule.** Reject invalid input with an explanation; retain
the entered message for correction rather than truncating it or silently
splitting it into jobs.

The message form has adjacent availability guidance derived from the existing connectivity, ownership, restart and capability gates. It introduces no second authority for job admission.

Saved CW schedule controls share one status region. Ordinary Refresh reads the schedule without replacing the draft; explicit Read saved schedule appears only for failed reads or action recovery and alone clears an unconfirmed action. Restore saved schedule confirms replacement of the complete editor and selects recurring delivery without transmitting. Existing schedules remain accessible while preparing Send once. Pause schedule appears only for an enabled schedule; pending pauses retain their durable-save guidance, and interrupted schedules expose Acknowledge interrupted schedule through the same pause endpoint. An already paused schedule explains the explicit save-and-start path to resume.

### LPF / band selector

The selector editor sits in Radio pins after amplifier timing and before GPIO drive. It uses the existing native fieldset, full-width inputs and selects, flat headings, buttons and concise saved/active status. Selection policy and release/settling fields use the three-column field grid, stacking at 650px; selector outputs and named frequency ranges repeat the same form pattern. Each selector names a Pico GPIO and polarity, while each range names a selector and inclusive whole-Hz limits. Add and remove actions stay beside their own group and return focus to the relevant entry or add button.

Read saved selectors, Save selectors and Discard selector entries remain separate actions. Reads preserve edited entries; discard restores the last read saved settings. Supported readback, a current device/boot identity and revision, writable availability, healthy storage and valid edited entries gate saving. A changed Pico or boot preserves the draft behind fresh readback and the explicit Use entries for this Pico action. A refused or unconfirmed save retains the entries and requires another read before saving again.

Validation uses one uniquely identified polite summary, with aria-invalid on the affected fields and aria-describedby connecting each invalid field to that explanation. Shared conflicts identify every affected field; editing clears stale invalid state. Help remains associated with valid fields. Observed status separately identifies saved policy, restart need, boot-active settings and current selection, including an unknown selection.

Adjacent help explains fixed / manual filtering and required automatic selection, release/settling units and bounds, and activation after restart. Saving never switches a relay or starts a job. Declared frequency coverage, GPIO observations and an active selector do not establish relay position or measured filtering.

### Standalone frequency

The standalone WSPR frequency form precedes the schedule-enable checkbox in
WSPR Configuration. It uses the existing native fieldset, label, full-width
text input and buttons. The label names Hz, the input requests a numeric keyboard,
and adjacent help explains whole-Hz entry without commas or decimals. An unset
frequency appears as a blank field; no band or frequency is preselected.

Read saved frequency, Save frequency and Discard frequency draft remain separate
actions. Readback preserves an edited draft; discard restores the last read
value, including an unset value. Inline polite status describes the saved value,
validation or recovery action, and invalid edited input carries `aria-invalid`.
Saving applies to future standalone WSPR jobs without a restart and never enables
schedules; schedule enablement remains a separate explicit action.

Editing and saving require supported capability, a current idle observation and
saved-state readback. Connection or boot changes invalidate that readback while
preserving the draft. A draft retained across a changed Pico or boot identity
requires fresh readback and the explicit Use entry for this Pico action before
saving. A refused or unconfirmed save preserves the entry and requires another
read; the browser does not repeat the save automatically.

### UTC date and time

Start times and schedule expiry use one UTC text field with adjacent Date and Time buttons. The field accepts an ISO date and a 24-hour time; both spaces and the ISO T separator are accepted. The UTC calendar and time selector replace the operating system's local-time popup. Opening either picker completes both components from current UTC when either is empty, while later selections preserve the other component. Complete invalid drafts remain visible for correction. Calendar navigation, Escape dismissal and focus return stay within the existing native-button and visible-focus treatment.

Calendar arithmetic and Today/Now actions use UTC, including near local midnight and daylight-saving changes. Observation timestamps name UTC, and past start values are rejected before job ownership is requested. The Pico remains the authority for clock readiness and final ARM admission.

### Finite-message preview

QRSS, FSKCW, and DFCW accept at most 32 characters including spaces. The preview
uses neutral preparation guidance for an untouched empty form. Edited invalid drafts receive errors. A complete preview shows character count, calculated event count against the device event ceiling,
and exact duration using integer nanoseconds formatted as minutes and seconds
with up to nine fractional digits. Supported characters are letters, numbers,
spaces, and `/ ? . , - + =`; unsupported characters and all-space messages
receive inline explanations.

The complete calculation includes the mode's mark and gap timing, repetitions,
between-repeat gaps, and the final tail. Duration must fit both the advertised
device limit and the 3,600-second ceiling. Event capacity is read from device
capabilities, with the source's 512-event fallback before capabilities arrive.
A message below 32 characters can still fail either capacity bound. Error text
states calculated duration and maximum, or required events and maximum, with a
specific correction. The server remains authoritative for acceptance.

### Status and progress

Notices and message preview use polite live status announcements. Job state,
RF output, ownership, and identity are observed data; RF output may explicitly
be unknown. Connection failure does not establish inactivity or completion.

**The Confirmed State Rule.** Estimated elapsed time may describe a matching
running job, but never replace its last confirmed state or turn a completed
estimate into confirmed completion.

Progress is tied to the observed boot and job identity. The running estimate
includes the status observation time; non-running states show the last confirmed
state. Failed status reads clear the current snapshot and label progress and
output unknown. Preserve these distinctions in future presentation changes.

### Provisioning and save recovery

Provisioning retains Wi-Fi first and optional station commissioning afterward.
A blank-device station refusal hides wording that assumes a saved network.
Accepted, confirmed and lost-contact Wi-Fi saves remain distinct. Reconnection
guidance uses only a validated matching-device hostname, preserves uncertainty,
and offers the router's current IP address as an alternative. Setup navigation
stays within the page inset. Every setup-Wi-Fi window has the fixed ten-minute
cap from actual activation; holding, release and traffic never extend it.

Unavailable profiles use the same light recovery shell, selectable identity and
an explicit USB Console `INFO` starting step. Alias links that merely return to
the unavailable page are omitted. Recovery does not imply an automatic reset. Cancel returns focus to the selected reset action. Provisioning transitions move focus to the page heading when the initiating form becomes hidden; background observations preserve focus.

Save reconciliation shows field-labelled differences between the browser draft,
saved progress and complete saved configuration, with matching fields counted. Differences are grouped by station, Wi-Fi and schedules/pins, with values in labelled rows. Omitted sparse overrides inherit the complete saved configuration; explicit clears remain visible.
The comparison updates on form input without requests, preserves invalid text,
and never copies a password into the comparison. Raw saved/active JSON is a
secondary native disclosure. Explicit readback and review still gate a new save;
matching values do not establish which earlier request saved them.

Active field boundaries use the existing button-border color, meeting 3:1
against both the white field and light canvas. Identify and the schedule-enable
label retain at least a 44px target. The intentional light-only theme, system
font, native controls and bounded local assets remain the design authority.

## Do's and Don'ts

- **Do** preserve the light canvas, navy header, and existing native form styles.
- **Do** expose exact duration, character count, and numerical event capacity.
- **Do** keep units, validation guidance, visible focus, and status announcements.
- **Do** preserve invalid drafts and explicit unknown device states.
- **Don't** truncate, split, or silently reduce an invalid message to fit limits.
- **Don't** use elapsed time or a lost connection as evidence of RF state.
- **Don't** import WsprryPi's separate theme or typography as an embedded UI rule.

The private `.impeccable/design.json` sidecar contains component previews and
metadata. Its generated tonal ramps are panel illustrations, not additional
implemented palette tokens.

### Pico password settings

The consumer login label is Pico password. Its default is the saved Wi-Fi password. Wi-Fi/Host presents a separate Pico password fieldset with current default/custom status, two masked confirmation fields, existing eye controls, inline errors and explicit save/default actions. Fields use two desktop columns and one mobile column. Saving signs out browser sessions and returns keyboard focus to the hostname lock; no password is placed in a URL, receipt or browser storage.

### NTP update timeout

Time and calibration is a separate section for the cross-mode NTP timeout and carrier correction. Both values load automatically; explicit read actions appear only when readback is unavailable or a write needs recovery. Timeout uses whole minutes, defaults to 60, accepts zero for indefinite NTP holdover after initial synchronization, and keeps saved and active values separate. Reads remain available during a transmission; saves require inactive, unowned output and a current target/revision. The help explains restart activation, initial synchronization, and uncertainty handling for finite and unlimited timeout selections. Unconfirmed writes require readback before another save, and changing Pico identity preserves the entry behind explicit review.

Transmission length appears immediately below the message and uses the same exact timing calculation as job submission. It updates before a frequency is entered and includes repeats, gaps and the final tail. Signed-out status uses a bounded public projection with five-second polling; unavailable readings become unknown with saved settings visible in full-opacity locked sections; mutations and job controls remain locked. Ordinary entry leaves the password modal closed. Only deliberate lock activation opens it and focuses the password. Subsequent status updates preserve focus and drafts.

### Contextual status console

Station status uses the status-heading role for accepted work or recovery and its compact variant on narrow screens; the empty-job headline is hidden. Context values use two flat columns and become single-column at 650px. Accepted work and Next transmission have separate labels; unique transmitter and connection observations follow in the same section. Routine explanations and the three timestamp fields are omitted. Recovery guidance remains visible when needed. Reset Pico and its feedback belong to Station status. Status transitions have one polite announcement; routine observations do not announce ticks. Unavailable status clears live values and disables controls without changing drafts or focus.

### Disclosures and access dialog

The hostname lock is a 44 px native button with local stroked SVG, a visually hidden state description and an action label. It is separate from the mutable hostname text node. Consumer and password SoftAP sessions use their real login/logout adapters; certificate access opens an explanation because the page cannot revoke a client certificate. The icon describes application access rather than HTTPS, ownership or RF safety.

Non-status operator groups use flat, border-separated native details/summary sections, closed by default. Explicit section bookmarks and unresolved save continuations reveal the needed content. Summary headings remain discoverable, and Top links have 44 px targets. Header view links wrap within the existing inset on narrow screens. Opening and closing retains the same form DOM, file selection and drafts; routine observations preserve disclosure choices.

The native access dialog uses the light canvas, one existing field border and the modal-backdrop color at 55 percent opacity. Section summaries and their nested headings share the section-heading role; view links retain the native header typography. It fits the dynamic viewport with internal scrolling for small screens and on-screen keyboards. Enter submits once, Escape or Close cancels and returns focus to the lock, and backdrop clicks leave it open. Errors remain within the dialog; passwords clear after attempts or dismissal. The native modal makes its background inert; an explicit Tab/Shift+Tab cycle keeps document focus among its visible enabled controls. Global mutation/reset warnings stay visible outside collapsed forms.

The Transmitter status panel keeps accepted jobs separate from Next transmission, which shows one eligible enabled automatic mode/message and is hidden when unavailable. Routine explanations, the three observation clocks and the engine identifier are omitted. Recovery guidance remains conditional and accessible. Manual RF correction (ppm) uses one three-decimal number, Wi-Fi retains connection/address, and Hostname shows the confirmed active full name.

Locked settings wrappers retain full-opacity disclosure headings and read-only content; native disabled form controls continue to enforce access. Reset Pico, Abort my job and Release control share one flex row in DOM order, wrapping naturally when the available width cannot fit their touch targets.

Station identity is grouped inside WSPR Configuration with its independent save/apply actions. Message type appears in the saved station draft summary, without provisional plan callouts. The schedule field uses interval/offset labels with UTC examples. Legacy station section bookmarks reveal WSPR Configuration. Raw boot-selector JSON is omitted from operator controls; restart and observed-selection status remain visible.

## Submission feedback

A native modal in the top layer dims the whole viewport, including an open access dialog. The foreground uses the existing compact corners, system type and 44 px buttons. Its operation text is a polite live status outside the busy main region. A dark color preference selects the navy foreground surface and light text; the underlying product keeps its established appearance. The backdrop uses 48% navy in light preference and 62% near-black in dark preference. There is no animation, spinner, flashing or motion. Cancel login, Lock controls and Abort this browser’s job are contextual actions in the foreground.

Contextual help uses original 16 px circle-question inline SVGs in help-text gray, with 44 px targets and existing amber keyboard focus. Icons sit beside their headings, disclosure titles, legends, labels or actions. Manual navigation retains its text.
The header places a light manual-home help icon after Station Control and Wi-Fi/Host navigation, aligned with the page content’s right edge on desktop and narrow screens.
Every disclosure and section has contextual help, including nested pin roles, saved progress, raw readback, dynamically mounted UDP controls and setup-result sections; more specific subheading help remains available.
