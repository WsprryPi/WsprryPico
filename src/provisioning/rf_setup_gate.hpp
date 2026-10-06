#pragma once

#include "wtp/job_service.hpp"

namespace wsprrypico::provisioning {
struct RfSetupAdmission {
    bool stop_verified = false;
    bool setup_accepted = false;
    bool manual_lease = false;
    bool service_inhibited = false;
    bool worker_inhibited = false;
    bool capture_healthy = false;
    bool scheduler_idle = false;
    bool stores_healthy = false;
    bool operation_pending = true;
    wtp::State state = wtp::State::Failed;
    bool owned = true;
    bool job_present = true;
    bool output_active = true;
};

inline bool rf_setup_allowed(const RfSetupAdmission& state) {
    // Local shutdown retains its acknowledged terminal job for STATUS/replay.
    // Its evidence must not keep a verified, inhibited setup lease read-only.
    const bool terminal = state.state == wtp::State::Aborted ||
                          state.state == wtp::State::Complete || state.state == wtp::State::Missed;
    const bool inactive_state =
        terminal || (state.state == wtp::State::Empty && !state.job_present);
    return state.stop_verified && state.setup_accepted && state.manual_lease &&
           state.service_inhibited && state.worker_inhibited && state.capture_healthy &&
           state.scheduler_idle && state.stores_healthy && !state.operation_pending &&
           inactive_state && !state.owned && !state.output_active;
}
} // namespace wsprrypico::provisioning
