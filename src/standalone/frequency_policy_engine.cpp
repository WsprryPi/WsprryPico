#include "standalone/frequency_policy_engine.hpp"

#include "application/frequency_policy.hpp"
#include "rf/calibration.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::standalone {
wtp::PrepareResult FrequencyPolicyEngine::prepare(const wtp::Job& job) {
    failure_ = nullptr;
    // Storage faults revoke all new execution, including qualified bands that
    // need no saved experimental permissions.
    if (!store_.healthy())
        return {};
    const auto& config = store_.config();
    const bool unqualified = store_.healthy() && config && config->allow_unqualified_frequency;
    const bool non_amateur = store_.healthy() && config && config->allow_non_amateur_frequency;
    const auto allowed = [&](std::uint64_t frequency) {
        return frequency >= minimum_ && frequency <= maximum_ &&
               application::frequency_allowed(frequency, unqualified, non_amateur);
    };
    for (const auto& event : job.events) {
        if (event.rf_on && (!event.frequency_nhz || !allowed(*event.frequency_nhz)))
            return {};
    }
    const auto selected = pair_frozen_ && frozen_ ? *frozen_ : selection();
    if ((selected.ppb && !job.allow_frequency_adjustment) ||
        (programmed_ != selected.ppb && !engine_.set_frequency_correction_ppb(selected.ppb)))
        return {};
    programmed_ = selected.ppb;
    auto prepared = engine_.prepare(job);
    if (!prepared.accepted)
        return prepared;
    rf::FilterCoverage coverage(boot_filters_);
    for (std::size_t i = 0; i < job.events.size(); ++i) {
        const auto& event = job.events[i];
        if (!event.rf_on || !event.frequency_nhz)
            continue;
        auto programmed = *event.frequency_nhz;
        for (const auto& adjustment : prepared.adjustments)
            if (adjustment.event_index == i)
                programmed = adjustment.realized_frequency_nhz;
        coverage.include(*event.frequency_nhz, programmed);
    }
    if (coverage.selection() == -2) {
        failure_ = "filter_coverage_required";
        return {};
    }
    // Quantization consent is independent of experimental consent. An engine
    // adjustment must not cross a policy or advertised hardware boundary.
    for (const auto& adjustment : prepared.adjustments) {
        if (!allowed(adjustment.realized_frequency_nhz))
            return {};
    }
    frozen_ = selected;
    return prepared;
}
FrequencyPolicyEngine::Selection FrequencyPolicyEngine::selection() const {
    Selection result;
    if (store_.config()) {
        result.ppb = store_.config()->manual_correction_ppb;
        result.generation = store_.config_sequence();
    }
    return result;
}
std::string FrequencyPolicyEngine::calibration_status(std::uint64_t) const {
    const auto next = selection();
    // Retain the v1 diagnostic shape, with no runnable or qualified NTP input.
    time::RateEstimate rejected;
    rejected.reason = "ntp_rf_rejected";
    return "{\"candidate\":" + time::rate_json(rejected) +
           ",\"candidate_correction_ppb\":null,\"candidate_uncertainty_ppb\":0,"
           "\"saved_ntp_available\":false,\"saved_ntp\":null,\"candidate_age_ns\":\"0\","
           "\"topology_supported\":false,\"independent_rf_verified\":false,"
           "\"ntp_rf_supported\":false,\"next_ppb\":" +
           std::to_string(next.ppb) + ",\"next_generation\":\"" + std::to_string(next.generation) +
           "\"" + ",\"next_source\":\"manual\",\"reason\":\"manual_mode\",\"prepared_ppb\":" +
           (frozen_ ? std::to_string(frozen_->ppb) : "null") +
           ",\"prepared_source\":" + (frozen_ ? "\"manual\"" : "null") +
           ",\"prepared_generation\":" +
           (frozen_ ? wtp::json::quote(std::to_string(frozen_->generation)) : "null") + "}";
}
} // namespace wsprrypico::standalone
