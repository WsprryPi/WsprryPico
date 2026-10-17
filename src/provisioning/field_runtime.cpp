#include "provisioning/field_runtime.hpp"

#include <algorithm>

namespace wsprrypico::provisioning {
namespace {
bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}
} // namespace

bool SoftApCoordinator::request_join_grace(std::uint64_t now_ms) {
    if (grace(now_ms))
        return false;
    if (expired_) {
        expired_ = false;
        activated_ = false;
    }
    grace_started_ms_ = now_ms;
    grace_active_ = true;
    return true;
}

bool SoftApCoordinator::request_manual_setup(std::uint64_t now_ms, bool shutdown_complete,
                                             bool button_held) {
    if (!shutdown_complete || manual_setup(now_ms) || manual_button_held_)
        return false;
    if (!requested_) {
        expired_ = false;
        activated_ = false;
    }
    manual_started_ms_ = now_ms;
    manual_active_ = true;
    manual_button_held_ = button_held;
    return true;
}

void SoftApCoordinator::manual_button_released(std::uint64_t now_ms) {
    (void)now_ms;
    manual_button_held_ = false; // Release never renews an activation deadline.
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

bool SoftApCoordinator::manual_setup(std::uint64_t now_ms) const {
    return manual_active_ && !expired_ &&
           (!activated_ || !elapsed(now_ms, activated_ms_, softap_manual_setup_ms));
}

void SoftApCoordinator::ready(bool value) {
    ready_ = value && requested_ && !expired_;
    if (ready_ && !activated_) {
        activated_ = true;
        activated_ms_ = last_poll_ms_;
    }
}

bool SoftApCoordinator::poll(std::uint64_t now_ms) {
    last_poll_ms_ = now_ms;
    if (activated_ && elapsed(now_ms, activated_ms_, softap_manual_setup_ms)) {
        expired_ = true;
        manual_active_ = grace_active_ = draining_ = false;
        ready_ = requested_ = false;
    }
    if (station_seen_ && station_usable_ &&
        elapsed(now_ms, station_changed_ms_, softap_station_stable_ms))
        fallback_armed_ = true;
    if (grace_active_ && !grace(now_ms))
        grace_active_ = false;
    if (manual_active_ && !manual_setup(now_ms))
        manual_active_ = false;
    if (station_seen_ && !station_usable_ && fallback_armed_ &&
        elapsed(now_ms, station_changed_ms_, softap_fallback_ms)) {
        fallback_armed_ = false;
        fallback_ = true;
        // A genuinely new outage may open another bounded window. An outage
        // already covered by the current window never extends that window.
        if (expired_) {
            expired_ = false;
            activated_ = false;
        }
    }
    const bool field_mode = access_.record() && access_.record()->field_mode;
    const bool retained = (!temporary_access_ && (token_records_ || reply_active_)) ||
                          grace(now_ms) || manual_setup(now_ms);
    if (fallback_ && station_usable_ &&
        elapsed(now_ms, station_changed_ms_, softap_station_stable_ms) &&
        (temporary_access_ || !retained) && !field_mode && !recovery_)
        fallback_ = false;
    const bool desired =
        !expired_ && (blank_profile_ || field_mode || recovery_ || fallback_ || retained);
    if (desired)
        draining_ = false;
    else if (!expired_ && temporary_access_ && requested_ && reply_active_ && !draining_) {
        draining_ = true;
        drain_started_ms_ = now_ms;
    }
    requested_ = desired || (!expired_ && draining_ && reply_active_ &&
                             !elapsed(now_ms, drain_started_ms_, softap_reply_drain_ms));
    if (!requested_)
        ready_ = false;
    return requested_;
}

SoftApStatus SoftApCoordinator::status(std::uint64_t now_ms) const {
    const bool manual = manual_setup(now_ms);
    return {requested_,
            ready_,
            no_profile_,
            access_.record() && access_.record()->field_mode,
            recovery_,
            fallback_,
            grace(now_ms),
            token_records_,
            reply_active_,
            manual,
            manual && manual_button_held_,
            draining_,
            expired_,
            activated_ && !expired_ && now_ms >= activated_ms_
                ? softap_manual_setup_ms - std::min(softap_manual_setup_ms, now_ms - activated_ms_)
                : 0};
}

SoftApSurface SoftApCoordinator::surface(bool clock_usable) const {
    if (no_profile_)
        return SoftApSurface::BlankReadOnly;
    return clock_usable ? SoftApSurface::Normal : SoftApSurface::ProvisionedPreClock;
}

IndicatorCode IndicatorController::identify(std::string_view request_id,
                                            std::string_view requested_device, bool authenticated,
                                            bool local, std::uint64_t now_ms) {
    if (!authenticated || !local)
        return IndicatorCode::AuthenticationRequired;
    if (!enabled_)
        return IndicatorCode::Invalid;
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
    if (!enabled_)
        return false;
    const auto active = pattern(now_ms);
    if (active == IndicatorPattern::Off)
        return false;
    const auto offset = active == IndicatorPattern::Identify
                            ? (now_ms - identify_started_ms_) % 2'000
                            : now_ms % 2'000;
    if (active == IndicatorPattern::SoftApReady)
        return offset < 150 || (offset >= 300 && offset < 450);
    return offset < 150 || (offset >= 300 && offset < 450) || (offset >= 600 && offset < 750);
}

void IndicatorController::poll(std::uint64_t now_ms) {
    if (identify_active_ && elapsed(now_ms, identify_started_ms_, 10'000))
        identify_active_ = false;
    if (transmit_output_) {
        // External selection is TX-only. Operational cues stay onboard.
        update(output_, desired(now_ms), operational_);
        update(*transmit_output_, enabled_ && transmitting_, selected_);
    } else {
        update(output_, enabled_ && (transmitting_ || desired(now_ms)), selected_);
    }
}

void IndicatorController::update(IndicatorOutput& output, bool value, OutputState& state) {
    if (state.known && state.on == value)
        return;
    if (!output.write(value)) {
        state.fault = true;
        state.known = false;
        return;
    }
    state.on = value;
    state.known = true;
}

void IndicatorController::poll_transmit(rf::IndicatorGate& gate, std::uint64_t now_ms) {
    const auto ticket = gate.requested();
    transmitting(ticket != 0);
    poll(now_ms);
    if (enabled_ && selected_.known && selected_.on)
        gate.acknowledge(ticket);
}

IndicatorStatus IndicatorController::status(std::uint64_t now_ms) const {
    return {pattern(now_ms),
            selected_.on,
            selected_.fault || operational_.fault,
            selected_.known,
            transmit_output_ ? operational_.on : selected_.on,
            transmit_output_ ? operational_.known : selected_.known,
            transmit_output_ ? operational_.fault : selected_.fault};
}
} // namespace wsprrypico::provisioning
