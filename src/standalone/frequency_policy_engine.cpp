#include "standalone/frequency_policy_engine.hpp"

#include "application/frequency_policy.hpp"
#include "rf/calibration.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::standalone {
wtp::PrepareResult FrequencyPolicyEngine::prepare(const wtp::Job& job) {
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
    const auto now = clock_ ? clock_->snapshot().monotonic_now_ns : 0;
    const auto selected = pair_frozen_ && frozen_ ? *frozen_ : selection(now);
    if ((selected.ppb && !job.allow_frequency_adjustment) ||
        (programmed_ != selected.ppb && !engine_.set_frequency_correction_ppb(selected.ppb)))
        return {};
    programmed_ = selected.ppb;
    auto prepared = engine_.prepare(job);
    if (!prepared.accepted)
        return prepared;
    // Quantization consent is independent of experimental consent. An engine
    // adjustment must not cross a policy or advertised hardware boundary.
    for (const auto& adjustment : prepared.adjustments) {
        if (!allowed(adjustment.realized_frequency_nhz))
            return {};
    }
    frozen_ = selected;
    return prepared;
}
FrequencyPolicyEngine::Selection FrequencyPolicyEngine::selection(std::uint64_t now) const {
    Selection result;
    if (store_.config()) {
        result.ppb = store_.config()->manual_correction_ppb;
        result.generation = store_.config_sequence();
    }
    if (std::string_view(fallback_reason(now)) == "qualified_ntp") {
        result.ppb = *time::oscillator_correction(candidate_);
        result.generation = candidate_.generation;
        result.ntp = true;
    }
    return result;
}
const char* FrequencyPolicyEngine::fallback_reason(std::uint64_t now) const {
    if (!store_.config() || !store_.config()->ntp_rf_calibration)
        return "manual_mode";
    if (!clock_ || !candidate_.qualified)
        return candidate_.reason;
    if (now < candidate_.sampled_ns || now - candidate_.sampled_ns > time::ntp_fresh_ns)
        return "stale";
    if (!time::oscillator_correction(candidate_))
        return "out_of_range";
    if (!topology_supported_)
        return "unsupported_clock_topology";
    if (!independent_rf_verified_)
        return "independent_rf_unverified";
    return "qualified_ntp";
}
std::string FrequencyPolicyEngine::calibration_status(std::uint64_t now) const {
    const auto next = selection(now);
    auto visible_candidate = candidate_;
    if (now < candidate_.sampled_ns || now - candidate_.sampled_ns > time::ntp_fresh_ns) {
        visible_candidate.qualified = false;
        visible_candidate.reason = "stale";
    }
    const auto correction = time::oscillator_correction(visible_candidate);
    const auto age = now >= candidate_.sampled_ns ? now - candidate_.sampled_ns : 0;
    // Reciprocal uncertainty: |dr/ds| <= 1e18/(1e9-200000)^2, plus integer rounding.
    const auto rf_uncertainty =
        (std::uint64_t(candidate_.uncertainty_ppb) * 1'001 + 999) / 1000 + 2;
    return "{\"candidate\":" + time::rate_json(visible_candidate) +
           ",\"candidate_correction_ppb\":" + (correction ? std::to_string(*correction) : "null") +
           ",\"candidate_uncertainty_ppb\":" + std::to_string(rf_uncertainty) +
           ",\"candidate_age_ns\":\"" + std::to_string(age) +
           "\",\"topology_supported\":" + (topology_supported_ ? "true" : "false") +
           ",\"independent_rf_verified\":false,\"next_ppb\":" + std::to_string(next.ppb) +
           ",\"next_generation\":\"" + std::to_string(next.generation) + "\"" +
           ",\"next_source\":" + wtp::json::quote(next.ntp ? "ntp" : "manual") +
           ",\"reason\":" + wtp::json::quote(fallback_reason(now)) +
           ",\"prepared_ppb\":" + (frozen_ ? std::to_string(frozen_->ppb) : "null") +
           ",\"prepared_source\":" +
           (frozen_ ? wtp::json::quote(frozen_->ntp ? "ntp" : "manual") : "null") +
           ",\"prepared_generation\":" +
           (frozen_ ? wtp::json::quote(std::to_string(frozen_->generation)) : "null") + "}";
}
} // namespace wsprrypico::standalone
