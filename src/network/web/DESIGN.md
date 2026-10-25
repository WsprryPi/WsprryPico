---
name: WsprryPico Station Control
description: Source-derived conventions for the embedded station control interface.
colors:
  header-navy: "#263e52"
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
  notice-surface: "#e7eef4"
  notice-border: "#b6c6d3"
  error-surface: "#fff0ed"
  error-border: "#bd6755"
  error-text: "#882b19"
typography:
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    lineHeight: 1.5
  label:
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

Body text and controls use the system stack recorded above, with controls
inheriting the surrounding font. Labels and status values are semibold; help
text is smaller and normal weight. The current page heading is `2rem` with
`1.2` line height; section headings and header identity are `1.25rem`. These
heading sizes describe the existing surface, not a new display-font identity.

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
buttons use white surfaces with dark text and a one-pixel border. Enabled hover
uses `brightness(.93)`; disabled buttons and fieldsets use `.6` opacity.
Keyboard focus has a three-pixel amber outline with a three-pixel offset. Programmatic section targets retain a one-rem scroll margin so the outline stays visible.
The header keeps its home link and station-control descriptor. A two-link task
navigation below the page heading selects Station/Transmission or Wi-Fi/Host.
The current area uses a thicker underline and `aria-current="page"`. Both links
retain the same document, session and drafts; only an explicit click scrolls to
the chosen area. Three local section shortcuts focus station identity, schedules/pins or message composition without changing the URL, receipt, session or form values. Shared access, observed transmitter status and save recovery
remain reachable in either area. Native profile-specific forms provide one
visible editor for each station/network field.

### Device identity

The device presentation uses the boot-active hostname as the one main heading in shared chrome,
above both task areas. Product and task labels stay unchanged. The heading and
tab title share one observation controller. Public names say to sign in;
authenticated readback labels the active name. A saved rename appears secondarily
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

### Standalone frequency

The standalone WSPR frequency form precedes the schedule-enable checkbox in
Schedules and radio pins. It uses the existing native fieldset, label, full-width
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

The consumer login label is Pico password. Its default is the saved Wi-Fi password. Wi-Fi/Host presents a separate Pico password fieldset with current default/custom status, two masked confirmation fields, existing eye controls, inline errors and explicit save/default actions. Fields use two desktop columns and one mobile column. Saving signs out browser sessions and returns keyboard focus to login; no password is placed in a URL, receipt or browser storage.

### NTP update timeout

The timeout control follows the existing native fieldset and read/save/discard pattern in Schedules and radio pins. It uses whole minutes, defaults to 60 minutes, and keeps saved and active values separate. Reads remain available during a transmission; saves require inactive, unowned output and a current target/revision. The help explains restart activation and the independent timing-uncertainty limit. Unconfirmed writes require readback before another save, and changing Pico identity preserves the entry behind explicit review.
