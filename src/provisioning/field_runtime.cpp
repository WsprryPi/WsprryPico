#include "provisioning/field_runtime.hpp"

namespace wsprrypico::provisioning {
namespace {
bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}
} // namespace

bool SoftApCoordinator::request_join_grace(std::uint64_t now_ms) {
    if (grace(now_ms))
        return false;
    grace_started_ms_ = now_ms;
    grace_active_ = true;
    return true;
}

void SoftApCoordinator::station(bool usable, std::uint64_t now_ms) {
    if (!station_seen_ || usable != station_usable_) {
        station_changed_ms_ = now_ms;
        station_seen_ = true;
    }
    station_usable_ = usable;
}

bool SoftApCoordinator::grace(std::uint64_t now_ms) const {
    return grace_active_ && !elapsed(now_ms, grace_started_ms_, softap_join_grace_ms);
}

bool SoftApCoordinator::poll(std::uint64_t now_ms) {
    if (grace_active_ && !grace(now_ms))
        grace_active_ = false;
    if (station_seen_ && !station_usable_ &&
        elapsed(now_ms, station_changed_ms_, softap_fallback_ms))
        fallback_ = true;
    const bool field_mode = access_.record() && access_.record()->field_mode;
    const bool retained = token_records_ || reply_active_ || grace(now_ms);
    if (fallback_ && station_usable_ &&
        elapsed(now_ms, station_changed_ms_, softap_station_stable_ms) && !retained &&
        !no_profile_ && !field_mode && !recovery_)
        fallback_ = false;
    requested_ = no_profile_ || field_mode || recovery_ || fallback_ || retained;
    if (!requested_)
        ready_ = false;
    return requested_;
}

SoftApStatus SoftApCoordinator::status(std::uint64_t now_ms) const {
    return {requested_,
            ready_,
            no_profile_,
            access_.record() && access_.record()->field_mode,
            recovery_,
            fallback_,
            grace(now_ms),
            token_records_,
            reply_active_};
}

SoftApSurface SoftApCoordinator::surface(bool clock_usable) const {
    if (no_profile_)
        return SoftApSurface::BlankReadOnly;
    return clock_usable ? SoftApSurface::Normal : SoftApSurface::ProvisionedPreClock;
}

IndicatorCode IndicatorController::identify(std::string_view request_id,
                                             std::string_view requested_device,
                                             bool authenticated, bool local,
                                             std::uint64_t now_ms) {
    if (!authenticated || !local)
        return IndicatorCode::AuthenticationRequired;
    if (requested_device != device_id_)
        return IndicatorCode::Invalid;
    if (request_id.empty())
        return IndicatorCode::Invalid;
    if (request_id == identify_request_)
        return IndicatorCode::Ok;
    if (identify_active_) {
        return IndicatorCode::Busy;
    }
    identify_request_.assign(request_id);
    identify_started_ms_ = now_ms;
    identify_active_ = true;
    return IndicatorCode::Ok;
}

IndicatorPattern IndicatorController::pattern(std::uint64_t now_ms) const {
    if (identify_active_ && !elapsed(now_ms, identify_started_ms_, 10'000))
        return IndicatorPattern::Identify;
    return softap_ready_ ? IndicatorPattern::SoftApReady : IndicatorPattern::Off;
}

bool IndicatorController::desired(std::uint64_t now_ms) const {
    const auto active = pattern(now_ms);
    if (active == IndicatorPattern::Off)
        return false;
    const auto offset = active == IndicatorPattern::Identify
                            ? (now_ms - identify_started_ms_) % 2'000
                            : now_ms % 2'000;
    if (active == IndicatorPattern::SoftApReady)
        return offset < 200;
    return offset < 150 || (offset >= 300 && offset < 450) ||
           (offset >= 600 && offset < 750);
}

void IndicatorController::poll(std::uint64_t now_ms) {
    if (identify_active_ && elapsed(now_ms, identify_started_ms_, 10'000))
        identify_active_ = false;
    const bool value = desired(now_ms);
    if (output_known_ && output_on_ == value)
        return;
    if (!output_.write(value)) {
        output_fault_ = true;
        output_known_ = false;
        return;
    }
    output_on_ = value;
    output_known_ = true;
}

IndicatorStatus IndicatorController::status(std::uint64_t now_ms) const {
    return {pattern(now_ms), output_on_, output_fault_};
}
} // namespace wsprrypico::provisioning
