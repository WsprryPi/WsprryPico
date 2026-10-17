#include "standalone/frequency_policy_engine.hpp"

#include "application/frequency_policy.hpp"

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
    auto prepared = engine_.prepare(job);
    if (!prepared.accepted)
        return prepared;
    // Quantization consent is independent of experimental consent. An engine
    // adjustment must not cross a policy or advertised hardware boundary.
    for (const auto& adjustment : prepared.adjustments) {
        if (!allowed(adjustment.realized_frequency_nhz))
            return {};
    }
    return prepared;
}
} // namespace wsprrypico::standalone
