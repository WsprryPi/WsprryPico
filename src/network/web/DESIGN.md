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
  field-border: "#8b9ba8"
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

This record applies to `src/network/web/index.html`, `style.css`, and `app.js`.
It captures the existing embedded operator interface after the finite-message
changes. No new brand metaphor, visual identity, or approved composition is
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
Keyboard focus has a three-pixel amber outline with a three-pixel offset.
The header has one home link and a station-control descriptor; it does not
establish a tab bar or expanded navigation system.

### Inputs and disclosures

Labels sit above full-width fields. Help stays beside its field and identifies
units, bounds, and consequences. Native `details`/`summary` disclose timing
settings and job-file loading; summaries have a `44px` minimum height. Focus
styling applies to inputs, textareas, selects, summaries, buttons, and links.
Disabled fieldsets reflect connectivity, ownership, and capability availability.

**The Preserved Draft Rule.** Reject invalid input with an explanation; retain
the entered message for correction rather than truncating it or silently
splitting it into jobs.

### Finite-message preview

QRSS, FSKCW, and DFCW accept at most 32 characters including spaces. The preview
shows character count, calculated event count against the device event ceiling,
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

This record is source documentation, not physical qualification. The finish
review handoff scored the exact-duration and numerical-event-ceiling fixes
resolved using local simulated API fixtures and desktop/mobile captures in
`build/phase11-5-r3-v2-ui-review-fixed/`. That evidence does not qualify physical
network behavior, target timing, or RF output.
