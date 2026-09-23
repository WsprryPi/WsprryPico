#include "time/controller_time.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::time {
namespace {
bool add(std::uint64_t left, std::uint64_t right, std::uint64_t& result) {
    if (right > std::numeric_limits<std::uint64_t>::max() - left)
        return false;
    result = left + right;
    return true;
}

void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}

bool bounded_identifier(std::string_view value) {
    return !value.empty() && value.size() <= 64 &&
           std::all_of(value.begin(), value.end(),
                       [](unsigned char byte) { return byte >= 33 && byte < 127; });
}
} // namespace

ActiveTimeSource ControllerTimeArbiter::label(ObservationSource source) {
    return source == ObservationSource::Sntp ? ActiveTimeSource::Sntp
                                             : ActiveTimeSource::Controller;
}

ControllerChallenge ControllerTimeArbiter::challenge(std::string_view principal,
                                                      std::string_view session,
                                                      std::string_view requested_device,
                                                      std::string nonce) {
    if (!now_ || !bounded_identifier(principal) || !bounded_identifier(session) ||
        !bounded_identifier(nonce))
        return {ControllerTimeCode::AuthenticationRequired};
    if (requested_device != device_id_)
        return {ControllerTimeCode::WrongDevice};
    if (pending_.live)
        return {ControllerTimeCode::SourceBusy};
    pending_.principal.assign(principal);
    pending_.session.assign(session);
    pending_.nonce = std::move(nonce);
    pending_.started_ns = now_(context_);
    pending_.live = true;
    return {ControllerTimeCode::Ok, pending_.nonce, pending_.started_ns};
}

bool ControllerTimeArbiter::challenge_delivered(std::string_view principal,
                                                std::string_view session,
                                                std::string_view requested_device,
                                                std::string_view nonce) {
    if (!pending_.live || !now_ || principal != pending_.principal ||
        session != pending_.session || requested_device != device_id_ || nonce != pending_.nonce)
        return false;
    // A controller cannot sample UTC in response to this challenge until the
    // complete indication is confirmed. Charge only post-delivery client/write
    // latency against the existing uncertainty budget; do not relax that budget.
    pending_.started_ns = now_(context_);
    return true;
}

void ControllerTimeArbiter::cancel_challenge(std::string_view principal,
                                             std::string_view session) {
    if (!pending_.live || principal != pending_.principal || session != pending_.session)
        return;
    clear(pending_.principal);
    clear(pending_.session);
    clear(pending_.nonce);
    pending_ = {};
}

ControllerTimeCode ControllerTimeArbiter::submit(std::string_view principal,
                                                 std::string_view session,
                                                 std::string_view requested_device,
                                                 std::string_view nonce,
                                                 std::uint64_t utc_ns) {
    if (!pending_.live)
        return ControllerTimeCode::Replay;
    const auto now = now_(context_);
    const bool binding = principal == pending_.principal && session == pending_.session &&
                         requested_device == device_id_ && nonce == pending_.nonce;
    const auto started = pending_.started_ns;
    clear(pending_.principal);
    clear(pending_.session);
    clear(pending_.nonce);
    pending_ = {};
    if (!binding)
        return requested_device == device_id_ ? ControllerTimeCode::AuthenticationRequired
                                              : ControllerTimeCode::WrongDevice;
    if (now < started || now - started > controller_challenge_lifetime_ns)
        return ControllerTimeCode::Timeout;
    std::uint64_t uncertainty{};
    if (!add(controller_fixed_uncertainty_ns, now - started, uncertainty) ||
        !add(uncertainty, controller_local_margin_ns, uncertainty) ||
        uncertainty > standalone_max_uncertainty_ns || utc_ns < sntp_min_utc_ns ||
        utc_ns >= sntp_max_utc_ns)
        return ControllerTimeCode::Uncertainty;
    const bool accepted = observe(ObservationSource::Controller, utc_ns, now, uncertainty,
                                  wtp::LeapState::Normal, {}, principal);
    if (accepted)
        return ControllerTimeCode::Ok;
    if (source_ == ActiveTimeSource::Disagreement)
        return ControllerTimeCode::Disagreement;
    return ControllerTimeCode::SourceBusy;
}

bool ControllerTimeArbiter::interval(const Observation& observation, std::uint64_t now,
                                     std::uint64_t& estimate,
                                     std::uint64_t& uncertainty) const {
    if (!observation.valid || now < observation.monotonic_ns)
        return false;
    const auto age = now - observation.monotonic_ns;
    if (age > controller_source_lifetime_ns || !add(observation.utc_ns, age, estimate))
        return false;
    const auto seconds = age / 1'000'000'000ULL;
    const auto remainder = age % 1'000'000'000ULL;
    if (seconds > std::numeric_limits<std::uint64_t>::max() / controller_drift_ppb)
        return false;
    auto drift = seconds * controller_drift_ppb;
    const auto fraction = remainder * controller_drift_ppb;
    drift += fraction / 1'000'000'000ULL + (fraction % 1'000'000'000ULL != 0);
    return add(observation.uncertainty_ns, drift, uncertainty) &&
           uncertainty <= standalone_max_uncertainty_ns;
}

bool ControllerTimeArbiter::current_valid(std::uint64_t now) const {
    std::uint64_t estimate{}, uncertainty{};
    return interval(current_, now, estimate, uncertainty);
}

bool ControllerTimeArbiter::overlaps(const Observation& left, const Observation& right,
                                     std::uint64_t now) const {
    std::uint64_t left_estimate{}, right_estimate{}, left_uncertainty{}, right_uncertainty{};
    if (!interval(left, now, left_estimate, left_uncertainty) ||
        !interval(right, now, right_estimate, right_uncertainty))
        return false;
    const auto difference = left_estimate > right_estimate ? left_estimate - right_estimate
                                                           : right_estimate - left_estimate;
    std::uint64_t total{};
    return add(left_uncertainty, right_uncertainty, total) && difference <= total;
}

bool ControllerTimeArbiter::accept(const Observation& observation) {
    if (!clock_.observe(observation.utc_ns, observation.monotonic_ns,
                        observation.uncertainty_ns, wtp::LeapState::Normal))
        return false;
    current_ = observation;
    recovery_ = {};
    source_ = label(observation.source);
    return true;
}

void ControllerTimeArbiter::disagreement(const Observation& observation) {
    clock_.invalidate();
    (void)observation;
    recovery_ = {};
    current_ = {};
    source_ = ActiveTimeSource::Disagreement;
}

bool ControllerTimeArbiter::observe(ObservationSource source, std::uint64_t utc_ns,
                                    std::uint64_t sampled_monotonic_ns,
                                    std::uint64_t uncertainty_ns, wtp::LeapState leap,
                                    std::optional<std::uint64_t> leap_transition_utc_ns,
                                    std::string_view principal) {
    if (!now_ || leap != wtp::LeapState::Normal || leap_transition_utc_ns ||
        uncertainty_ns > standalone_max_uncertainty_ns || utc_ns < sntp_min_utc_ns ||
        utc_ns >= sntp_max_utc_ns ||
        (source == ObservationSource::Controller && principal.empty()) ||
        (source == ObservationSource::Sntp && !principal.empty()))
        return false;
    const auto now = now_(context_);
    Observation candidate{source, utc_ns, sampled_monotonic_ns, uncertainty_ns,
                          std::string(principal), true};
    std::uint64_t estimate{}, grown{};
    if (!interval(candidate, now, estimate, grown))
        return false;
    if (source_ == ActiveTimeSource::Disagreement) {
        if (!recovery_.valid || recovery_.source != source ||
            recovery_.principal != candidate.principal || !overlaps(recovery_, candidate, now)) {
            recovery_ = candidate;
            return false;
        }
        return accept(candidate);
    }
    if (!current_valid(now)) {
        current_ = {};
        source_ = ActiveTimeSource::None;
        return accept(candidate);
    }
    if (current_.source == ObservationSource::Sntp && source == ObservationSource::Controller)
        return false;
    if (current_.source == ObservationSource::Controller && source == ObservationSource::Controller &&
        current_.principal != candidate.principal)
        return false;
    if (!overlaps(current_, candidate, now)) {
        disagreement(candidate);
        return false;
    }
    return accept(candidate);
}

void ControllerTimeArbiter::invalidate(ObservationSource source) {
    if (source_ == label(source) || source_ == ActiveTimeSource::Disagreement) {
        clock_.invalidate();
        current_ = {};
        recovery_ = {};
        source_ = ActiveTimeSource::None;
    }
}

ControllerTimeStatus ControllerTimeArbiter::status() const {
    ControllerTimeStatus result;
    result.source = source_;
    result.disagreement = source_ == ActiveTimeSource::Disagreement;
    if (!now_ || !current_.valid)
        return result;
    const auto now = now_(context_);
    std::uint64_t estimate{};
    if (!interval(current_, now, estimate, result.uncertainty_ns)) {
        if (!result.disagreement)
            result.source = ActiveTimeSource::None;
        return result;
    }
    result.age_ns = now - current_.monotonic_ns;
    if (current_.source == ObservationSource::Controller)
        result.principal = current_.principal;
    return result;
}
} // namespace wsprrypico::time
