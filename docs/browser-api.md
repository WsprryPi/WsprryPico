# Shared browser-facing JSON API

Status: design direction and proposed resources.

Accepted direction: reuse WsprryPi browser assets and UX through an API implemented by both Linux services and Pico firmware. This does not require a shared repository today.

## Proposed resources

| Resource | Responsibility |
|---|---|
| /api/v1/capabilities | Implemented modes, engines, limits and available management features |
| /api/v1/status | Job/owner/output state, clock health and terminal result |
| /api/v1/config | Validated station and device configuration with revision checking |
| /api/v1/schedules | Bounded standalone schedule definitions |
| /api/v1/jobs | Submit complete application jobs and inspect their status |
| /api/v1/jobs/{id}/abort | Request cancellation through the common job service |

Paths and schemas are proposals, not existing endpoints. Version the browser contract explicitly; its version need not equal WTP or firmware versions.

The browser API includes configuration and scheduling, while WTP is focused on transmitter interoperability. Both adapters call the same validation and execution service. A browser request must not introduce a separate RF start path.

A portable front end consumes capabilities and handles unsupported features explicitly. Keep Linux maintenance operations out of Pico capabilities. Preserve familiar station configuration, band selection, schedules and status where practical.

Before implementation: inventory PHP-rendered state, JavaScript dependencies, assets and licensing; define errors, precision, config revisions, bounded logs/pagination, network authentication and protection for browser-originated mutations; measure compressed asset size and peak memory. Audit existing endpoint semantics before attempting any WsprryPi migration.

Initial read-only inventory found WsprryPi-UI/data/views/{operation,config,logs,maintenance}.php and shared PHP page-shell/state helpers. This identifies likely coupling; it does not establish how much code is portable.
