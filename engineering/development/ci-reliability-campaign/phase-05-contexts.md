# Browser migration obligation matrix

The immediate prechange source is e09799ba (executable pilot 61c5eb44).
All entries use synthetic devices and actual production handlers/crypto.

| Suite / invocation | Fixture contexts | Browser contexts and distinct obligations |
| --- | --- | --- |
| Frequency, ordinary | consumer-lan | Shipped assets, independent dial read/save/refusal, accessibility, responsive captures |
| Frequency, first-use network | first-use-network | Fresh journal, missing station, first WSPR transmission trial |
| Frequency, explicit opt-ins | engineering refusal; first-use usb/overlay/network-backing | Preserve argument mapping, original profile offsets, and separate journals; not ordinary invocations |
| Session pilot | consumer-lan | Qualified expiry/drafts/refusal, four captures, independent journal oracle |
| Submission | consumer-lan | Shipped assets, keyboard/touch/modal, held requests, cancellation, lost replies, logging, abort, suspension |
| Sections, consumer | consumer-lan | Shipped assets, help/popups, keyboard/focus, files/History, lock/logout, RF/GPS controls, captures |
| Sections, engineering | engineering | Separate command/browser/journal; certificate authority, help, Si5351/GPS controls |
| Sections, field opt-in | consumer-ap | Preserve AP port/authority and field-clock/settings checks; no hardware execution |
| Message-frequency | consumer-lan and engineering | One invocation, two sequential browsers, independent profiles, both schedule/control surfaces and captures |
| Recovery | direct production fixture | One browser, three isolated browser contexts; drafts, foreign-client saves, lost replies, session limits, recovery/retirement |
| Hostname | direct A/B fixtures | Two device tabs, reboot, identity, pending cancellation, long names, wrong-device refusal, captures |
| Organization | direct A/B and replacement fixtures | Two device tabs, commissioning/recovery, replacement/reboot, lost replies, navigation and optional axe/captures |
| WSPR | direct fixtures and replacement | Shipped bundle, Type 2/3, station/profile revisions, saved/applied distinctions and captures |
| Progress | direct fixtures and replacement | Consumer/engineering routes, held/lost replies, partial/null fields, stale/future schemas, optional axe/captures |
| Operator cleanup | direct session fixture and source/shipped assets | Preserve intentional source HTML plus minified script/bundle path, status, filters, grids, GPIO, uncertainty/recovery, captures |

These eleven entry files produce thirteen ordinary command invocations. The
message loop launches two browsers within one command; hostname/organization
create additional tabs, recovery creates three isolated contexts. These are
separate counting units. Seven ordinary review-server invocations previously
started seventy drivers; their used definitions total eight. Direct-fixture
starts/replacements and regression processes are additional, not savings.
No capture option may skip a layout or behavioral assertion during migration.
Field and first-use opt-ins remain reachable; hardware entry points are outside
this software migration and are not executed or retired.
