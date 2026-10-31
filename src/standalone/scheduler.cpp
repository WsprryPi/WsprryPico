#include "standalone/scheduler.hpp"

#include "encoding/wspr.hpp"
#include "time/mapping.hpp"
#include "time/sntp.hpp"
#include "wtp/codec.hpp"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <cstdio>
#include <limits>

namespace wsprrypico::standalone {
namespace {
constexpr std::uint64_t ns = 1'000'000'000ULL;
constexpr std::uint64_t frame_duration = 110'592'000'000ULL;
constexpr std::uint64_t slot_duration = 120 * ns;
constexpr auto local_id = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";
std::string id(std::uint64_t value) {
    char text[33];
    std::snprintf(text, sizeof(text), "eeeeeeeeeeeeeeee%016llx",
                  static_cast<unsigned long long>(value));
    return text;
}
std::string error(std::string_view why) {
    return "{\"ok\":false,\"error\":\"" + std::string(why) + "\"}\n";
}
wtp::PayloadDigest network_digest(const Config& config) {
    const auto text = wtp::json::quote(config.ssid) + "," + wtp::json::quote(config.password) +
                      "," + wtp::json::quote(config.ntp_ipv4);
    return wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
}
bool clock_ready(const wtp::ClockSnapshot& now, const wtp::ServiceConfig& config) {
    return now.state != wtp::ClockState::Unsynchronized && now.leap == wtp::LeapState::Normal &&
           now.uncertainty_ns <= config.maximum_arm_uncertainty_ns &&
           (now.state != wtp::ClockState::Holdover ||
            (config.maximum_holdover_age_ns &&
             now.sync_age_ns <= config.maximum_holdover_age_ns)) &&
           now.utc_now_ns >= time::sntp_min_utc_ns && now.utc_now_ns < time::sntp_max_utc_ns;
}
} // namespace
Scheduler::Scheduler(Store& store, wtp::JobService& service) : store_(store), service_(service) {
    active_filters_ = store_.filters();
    if (store_.config()) {
        active_network_ = network_digest(*store_.config());
        active_pins_ = store_.config()->pins;
        active_gpio_drive_ma_ = store_.config()->gpio_drive_ma;
        active_amplifier_timing_ = store_.config()->amplifier_timing;
        active_ntp_timeout_s_ = store_.config()->ntp_timeout_s;
        boot_configured_ = store_.healthy();
    }
}
wtp::Response Scheduler::request(std::string_view operation, wtp::RequestBody body) {
    wtp::Request r;
    r.principal = "standalone-local";
    r.session_id = local_id;
    r.request_id = id(++sequence_);
    r.operation = operation;
    r.body = std::move(body);
    r.payload_digest = wtp::sha256(
        std::span(reinterpret_cast<const std::uint8_t*>(r.request_id.data()), r.request_id.size()));
    // Account for this request's identities before checking the LOAD reserve.
    // A check before constructing Request can pass while these allocations
    // leave too little headroom for JobService's identical admission gate.
    // This local producer owns the decoded job, so optional USB buffers may
    // be reclaimed without invalidating its input or reducing either reserve.
    if (operation == "LOAD") {
        last_load_stage_ = 1;
        last_load_free_before_ = wtp::available_memory ? wtp::available_memory() : SIZE_MAX;
        const auto* job = std::get_if<wtp::Job>(&r.body);
        const bool admitted =
            job && wtp::authoritative_memory_admitted(service_.preparation_memory_bytes(*job));
        last_load_free_after_ = wtp::available_memory ? wtp::available_memory() : SIZE_MAX;
        if (!admitted) {
            last_load_stage_ = 2;
            wtp::Response response;
            response.error = wtp::ErrorCode::InternalError;
            return response;
        }
    }
    auto response = service_.handle_internal(std::move(r));
    if (operation == "LOAD")
        last_load_stage_ = response.ok ? 4 : 3;
    return response;
}
bool Scheduler::idle() const {
    const auto s = service_.activity();
    return !service_.maintenance() && !hardware_application_failed_ && !s.owned &&
           !s.output_active && s.state != wtp::State::Armed && s.state != wtp::State::Running &&
           s.state != wtp::State::Failed;
}
bool Scheduler::reset_permitted() const {
    if (idle())
        return true;
    const auto s = service_.activity();
    // Explicit Console reset can recover a latched fault only without an owner,
    // RF output, or an enabled autonomous schedule. The caller must still verify
    // engine disable before actually resetting; this does not clear WTP state.
    const bool recoverable_fault = s.state == wtp::State::Failed ||
                                   (hardware_application_failed_ && service_.output_inhibited());
    return recoverable_fault && !s.owned && !s.output_active && s.state != wtp::State::Loaded &&
           s.state != wtp::State::Armed && s.state != wtp::State::Running && store_.healthy() &&
           store_.config() && !store_.config()->enabled;
}
void Scheduler::poll() {
    service_.poll();
    if (service_.maintenance())
        return; // No slot/watermark reservation while USB maintenance is pending.
    if (poll_message())
        return;
    if (pair_) {
        poll_pair();
        return;
    }
    if (!store_.healthy() || !store_.config() || !store_.config()->enabled || reboot_required_ ||
        suspended_ || !idle())
        return;
    const auto now = service_.clock_snapshot();
    if (!clock_ready(now, service_.config()))
        return;
    std::uint64_t candidate = std::numeric_limits<std::uint64_t>::max();
    for (const auto& schedule : store_.config()->schedules) {
        const auto period = std::uint64_t{schedule.period_s} * ns;
        const auto phase = std::uint64_t{schedule.phase_s} * ns + ns;
        auto slot = (now.utc_now_ns / period) * period + phase;
        if (slot <= now.utc_now_ns)
            slot += period;
        if (slot > store_.watermark())
            candidate = std::min(candidate, slot);
    }
    if (candidate <= now.utc_now_ns || candidate - now.utc_now_ns > 10 * ns ||
        candidate - now.utc_now_ns < 2 * ns)
        return;
    const auto& c = *store_.config();
    if (!c.wspr_dial_frequency_hz) {
        last_error_ = wtp::ErrorCode::FrequencyRejected;
        return;
    }
    const auto tones = wspr_tones(*c.wspr_dial_frequency_hz);
    if (!tones) {
        last_error_ = wtp::ErrorCode::FrequencyRejected;
        return;
    }
    const auto plan = encoding::wspr_plan(c.callsign, c.locator, c.power_dbm);
    if (!plan) {
        last_error_ = wtp::ErrorCode::UnsupportedMode;
        return;
    }
    const auto final_slot = candidate + (plan->count - 1) * slot_duration;
    const auto expiry = c.expires_utc_s * ns;
    // Include the second frame's entire accepted launch second for a pair.
    // Keep the previously accepted single-frame admission policy unchanged.
    std::uint64_t utc_frame_duration{};
    if (!time::duration_utc_bound(frame_duration, now, utc_frame_duration))
        return;
    const auto required_tail = utc_frame_duration + (plan->count == 2 ? ns - 1 : 0);
    if (expiry && (final_slot >= expiry || expiry - final_slot < required_tail))
        return;
    if (plan->count == 2) {
        std::uint64_t complete_raw_end{};
        if (final_slot > time::sntp_max_utc_ns - required_tail ||
            !time::inverse(now, final_slot + required_tail, complete_raw_end))
            return;
    }
    if (!request("HELLO", wtp::HelloBody{{"WTP/1"}}).ok)
        return;
    auto response = request("CLAIM", wtp::ClaimBody{local_id, plan->count == 2 ? 60000U : 5000U});
    if (!response.ok) {
        last_error_ = response.error;
        return;
    }
    // Durable at-most-once reservation BEFORE preparation/arming. A failure
    // after this point skips the occurrence; it never retries an ambiguous job.
    if (!store_.reserve(final_slot)) {
        (void)request("RELEASE");
        return;
    }
    last_frame_count_ = plan->count;
    last_frame_ = 1;
    service_.freeze_pair_calibration(plan->count == 2);
    if (plan->count == 2)
        pair_ = Pair{*plan,
                     final_slot,
                     store_.config_sequence(),
                     now.monotonic_now_ns + 30 * ns,
                     now.utc_now_ns,
                     now.monotonic_now_ns,
                     now.uncertainty_ns,
                     now,
                     *tones};
    if (!prepare_frame(plan->frames[0], candidate, *tones))
        pair_.reset();
}
std::uint64_t Scheduler::message_lead_ns() const {
    const auto minimum = service_.config().minimum_arm_lead_ns;
    return minimum > UINT64_MAX - ns ? UINT64_MAX : std::max(message_preparation_ns, minimum + ns);
}
std::optional<std::uint64_t> Scheduler::next_message_start() const {
    if (!store_.healthy() || !store_.message_schedule() || !store_.message_schedule()->enabled ||
        suspended_ || message_pause_pending_ || message_recovery_required() || reboot_required_)
        return {};
    const auto now = service_.clock_snapshot();
    if (!clock_ready(now, service_.config()) || message_lead_ns() > time::sntp_max_utc_ns ||
        now.utc_now_ns > time::sntp_max_utc_ns - message_lead_ns())
        return {};
    const auto& schedule = *store_.message_schedule();
    const auto next =
        next_message_slot(schedule, now.utc_now_ns + message_lead_ns(), store_.watermark());
    if (!next)
        return {};
    const auto measured = encoding::measure_message(schedule.message, service_.config().max_events,
                                                    service_.config().max_job_duration_ns);
    std::uint64_t duration{};
    if (!measured.error.empty() ||
        !time::duration_utc_bound(measured.calculated_duration_ns, now, duration))
        return {};
    const auto expiry = schedule.expires_utc_s * ns;
    if (expiry && (*next >= expiry || duration > expiry - *next))
        return {};
    return next;
}
std::optional<std::uint64_t> Scheduler::next_wspr_start() const {
    const auto now = service_.clock_snapshot();
    if (!store_.healthy() || !store_.config() || !store_.config()->enabled || suspended_ ||
        reboot_required_ || !clock_ready(now, service_.config()) || !idle() || pair_ ||
        (store_.message_schedule() && store_.message_schedule()->enabled))
        return {};
    const auto& c = *store_.config();
    if (!c.wspr_dial_frequency_hz)
        return {};
    const auto plan = encoding::wspr_plan(c.callsign, c.locator, c.power_dbm);
    if (!plan)
        return {};
    auto candidate = std::numeric_limits<std::uint64_t>::max();
    for (const auto& schedule : c.schedules) {
        const auto period = std::uint64_t{schedule.period_s} * ns;
        const auto phase = std::uint64_t{schedule.phase_s} * ns + ns;
        if (!period)
            continue;
        const auto earliest = std::max(now.utc_now_ns + 2 * ns, store_.watermark() + 1);
        auto slot = (earliest / period) * period + phase;
        if (slot < earliest)
            slot += period;
        candidate = std::min(candidate, slot);
    }
    std::uint64_t duration{};
    if (candidate == std::numeric_limits<std::uint64_t>::max() ||
        !time::duration_utc_bound(frame_duration, now, duration))
        return {};
    const auto tail =
        (plan->count - 1) * slot_duration + duration + (plan->count == 2 ? ns - 1 : 0);
    if (candidate >= time::sntp_max_utc_ns || tail > time::sntp_max_utc_ns - candidate ||
        (c.expires_utc_s &&
         (candidate >= c.expires_utc_s * ns || tail > c.expires_utc_s * ns - candidate)))
        return {};
    return candidate;
}
std::string Scheduler::message_status() const {
    const auto& schedule = store_.message_schedule();
    const auto now = service_.clock_snapshot();
    auto next = next_message_start();
    if (message_job_ && service_.activity().state == wtp::State::Armed)
        next = store_.last_message_start();
    std::string state = "not_configured";
    if (!store_.healthy())
        state = "unavailable";
    else if (message_recovery_required())
        state = "recovery_required";
    else if (message_pause_pending_)
        state = "pausing";
    else if (message_job_)
        state = wtp::state_name(service_.activity().state);
    else if (schedule) {
        if (!schedule->enabled)
            state = "paused";
        else if (suspended_)
            state = "suspended";
        else if (reboot_required_)
            state = "restart_required";
        else if (!clock_ready(now, service_.config()))
            state = "waiting_for_time";
        else if (!encoding::measure_message(schedule->message, service_.config().max_events,
                                            service_.config().max_job_duration_ns)
                      .error.empty())
            state = "unavailable";
        else if (!next)
            state = "expired";
        else
            state = idle() ? "waiting" : "waiting_for_transmitter";
    }
    return "{\"saved\":" + (schedule ? serialize_message_schedule(*schedule) : "null") +
           ",\"state\":" + wtp::json::quote(state) +
           ",\"pause_pending\":" + (message_pause_pending_ ? "true" : "false") +
           ",\"next_start_utc_ns\":" + (next ? wtp::json::quote(std::to_string(*next)) : "null") +
           ",\"last_start_utc_ns\":" +
           (store_.last_message_start()
                ? wtp::json::quote(std::to_string(store_.last_message_start()))
                : "null") +
           ",\"last_job_id\":" +
           (last_message_job_.empty() ? "null" : wtp::json::quote(last_message_job_)) +
           ",\"last_result\":" +
           (last_message_result_.empty() ? "null" : wtp::json::quote(last_message_result_)) +
           ",\"last_error\":" +
           (message_error_ == wtp::ErrorCode::None ? "null" : wtp::error_json(message_error_)) +
           "}";
}
bool Scheduler::finish_message_pause() {
    if (!idle() || message_job_)
        return true; // Pending, never interrupt an accepted job.
    if (store_.message_schedule()) {
        auto paused = *store_.message_schedule();
        paused.enabled = false;
        if (!store_.save_message_schedule(paused))
            return false;
    }
    if (!store_.clear_message_flight())
        return false;
    message_saved();
    return true;
}
bool Scheduler::pause_message() {
    if (!store_.message_schedule() && !store_.message_in_flight())
        return true;
    message_pause_pending_ = true;
    return finish_message_pause();
}
bool Scheduler::poll_message() {
    if (message_job_) {
        auto current = service_.status();
        const auto terminal =
            std::find_if(current.terminal_records.begin(), current.terminal_records.end(),
                         [&](const auto& t) { return t.job_id == *message_job_; });
        if (terminal == current.terminal_records.end()) {
            if (current.job_id == message_job_ &&
                (current.state == wtp::State::Armed || current.state == wtp::State::Running))
                return true;
            message_recovery_required_ = true;
            message_error_ = wtp::ErrorCode::InvalidState;
            message_job_.reset();
            return true;
        }
        last_message_result_ = wtp::state_name(terminal->state);
        if (terminal->state != wtp::State::Complete || terminal->output_active ||
            terminal->error != wtp::ErrorCode::None) {
            message_recovery_required_ = true;
            message_error_ = terminal->error == wtp::ErrorCode::None ? wtp::ErrorCode::InvalidState
                                                                     : terminal->error;
            message_job_.reset();
            return true;
        }
        if (current.output_active || current.state == wtp::State::Armed ||
            current.state == wtp::State::Running)
            return true;
        if (current.owner_id == local_id && current.job_id == message_job_) {
            if (!request("RELEASE").ok) {
                message_recovery_required_ = true;
                return true;
            }
        }
        if (!idle())
            return true;
        if (!store_.clear_message_flight()) {
            message_recovery_required_ = true;
            return true;
        }
        message_job_.reset();
        if (message_pause_pending_ && !finish_message_pause())
            message_recovery_required_ = true;
        return true;
    }
    if (message_pause_pending_) {
        if (!finish_message_pause())
            message_recovery_required_ = true;
        return true;
    }
    if (message_recovery_required())
        return true;
    if (!store_.message_schedule() || !store_.message_schedule()->enabled)
        return false;
    if (pair_ || !idle() || suspended_ || reboot_required_ || !store_.healthy())
        return true;
    const auto next = next_message_start();
    if (!next)
        return true;
    const auto now = service_.clock_snapshot();
    if (*next - now.utc_now_ns > std::max(10 * ns, message_lead_ns() + ns))
        return true;
    const auto& schedule = *store_.message_schedule();
    auto message = schedule.message;
    message.job_id = "dddddddddddddddd" + id(*next).substr(16);
    auto compiled = encoding::compile_message(message, service_.config().max_events,
                                              service_.config().max_job_duration_ns);
    if (!compiled.job) {
        message_recovery_required_ = true;
        message_error_ = wtp::ErrorCode::InvalidMessage;
        return true;
    }
    if (!request("HELLO", wtp::HelloBody{{"WTP/1"}}).ok)
        return true;
    const auto claimed = request("CLAIM", wtp::ClaimBody{local_id, 5000});
    if (!claimed.ok)
        return true;
    if (!store_.reserve_message(*next)) {
        (void)request("RELEASE");
        message_recovery_required_ = true;
        return true;
    }
    message_job_ = message.job_id;
    last_message_job_ = message.job_id;
    last_message_result_.clear();
    auto response = request("LOAD", std::move(*compiled.job));
    if (response.ok)
        response = request("ARM", wtp::ArmBody{message.job_id, *next,
                                               service_.config().maximum_arm_uncertainty_ns});
    if (!response.ok) {
        message_error_ = response.error;
        message_recovery_required_ = true;
        const auto current = service_.status();
        if (current.owner_id == local_id && !current.output_active &&
            current.state != wtp::State::Armed && current.state != wtp::State::Running &&
            current.state != wtp::State::Failed)
            (void)request("RELEASE");
        message_job_.reset();
    }
    return true;
}
bool Scheduler::prepare_frame(const encoding::WsprFrame& frame, std::uint64_t slot,
                              const std::array<std::uint64_t, 4>& tones) {
    wtp::Job job{id(slot), "rf-events/1", "wspr", frame_duration, {}, true};
    if (!job.events.reserve(162)) {
        last_error_ = wtp::ErrorCode::InternalError;
        (void)request("RELEASE");
        return false;
    }
    for (unsigned i = 0; i < frame.symbols.size(); ++i) {
        const auto start = (std::uint64_t{i} * 2'048'000'000ULL + 1) / 3;
        const auto end = (std::uint64_t{i + 1} * 2'048'000'000ULL + 1) / 3;
        if (!job.events.push_back({start, end - start, true, tones[frame.symbols[i]]})) {
            last_error_ = wtp::ErrorCode::InternalError;
            (void)request("RELEASE");
            return false;
        }
    }
    last_job_ = job.job_id;
    auto response = request("LOAD", std::move(job));
    if (response.ok)
        response = request(
            "ARM", wtp::ArmBody{last_job_, slot, service_.config().maximum_arm_uncertainty_ns});
    last_error_ = response.error;
    if (!response.ok)
        (void)request("RELEASE");
    return response.ok;
}
void Scheduler::cancel_pair(wtp::ErrorCode reason) {
    pair_.reset();
    service_.freeze_pair_calibration(false);
    last_error_ = reason;
    const auto s = service_.status();
    if (s.owner_id && *s.owner_id == local_id) {
        if (s.job_id && *s.job_id == last_job_ &&
            (s.state == wtp::State::Loaded || s.state == wtp::State::Armed ||
             s.state == wtp::State::Running)) {
            const auto aborted = request("ABORT", wtp::AbortBody{last_job_});
            if (!aborted.ok) {
                last_error_ = aborted.error;
                return; // Retain failed/output-unknown authority for explicit recovery.
            }
        }
        const auto released = request("RELEASE");
        if (!released.ok)
            last_error_ = released.error;
    }
}
void Scheduler::poll_pair() {
    const auto now = service_.clock_snapshot();
    const auto s = service_.status();
    std::uint64_t projected{};
    const bool mapping_valid = time::project(pair_->mapping, now.monotonic_now_ns, projected);
    std::uint64_t prior_growth{};
    const bool growth_valid =
        now.monotonic_now_ns >= pair_->anchor_monotonic &&
        time::growth(now.monotonic_now_ns - pair_->anchor_monotonic,
                     50'000 + pair_->mapping.rate_uncertainty_ppb, prior_growth);
    const auto mapping_error =
        projected > now.utc_now_ns ? projected - now.utc_now_ns : now.utc_now_ns - projected;
    if (!store_.healthy() || !store_.config() || !store_.config()->enabled ||
        store_.config_sequence() != pair_->config_sequence || reboot_required_ || suspended_ ||
        !mapping_valid || !growth_valid || !clock_ready(now, service_.config()) ||
        now.utc_now_ns < pair_->anchor_utc || now.monotonic_now_ns < pair_->anchor_monotonic ||
        (mapping_error > pair_->anchor_uncertainty + prior_growth &&
         mapping_error - pair_->anchor_uncertainty - prior_growth > now.uncertainty_ns) ||
        !s.owner_id || *s.owner_id != local_id || !s.job_id || *s.job_id != last_job_ ||
        (s.state != wtp::State::Armed && s.state != wtp::State::Running &&
         s.state != wtp::State::Complete)) {
        cancel_pair(wtp::ErrorCode::InvalidState);
        return;
    }
    if (pair_->frame == 1 && s.state == wtp::State::Complete) {
        cancel_pair(wtp::ErrorCode::None);
        return;
    }
    if (now.monotonic_now_ns >= pair_->renew_at) {
        const auto renewed = request("RENEW", wtp::RenewBody{local_id, 60000});
        if (!renewed.ok) {
            cancel_pair(renewed.error);
            return;
        }
        pair_->renew_at = now.monotonic_now_ns + 30 * ns;
    }
    if (pair_->frame != 0 || s.state != wtp::State::Complete)
        return;
    const auto slot = pair_->second_slot;
    if (slot <= now.utc_now_ns || slot - now.utc_now_ns < 2 * ns) {
        cancel_pair(wtp::ErrorCode::MissedStart);
        return;
    }
    if (slot - now.utc_now_ns > 10 * ns)
        return;
    last_frame_ = 2;
    pair_->frame = 1;
    if (!prepare_frame(pair_->plan.frames[1], slot, pair_->tones))
        pair_.reset();
}
std::string Scheduler::status(const wtp::ServiceStatus* observation) const {
    const auto s = observation ? *observation : service_.status();
    const auto clock = service_.clock_snapshot();
    std::string station = "null", schedules = "[]";
    if (store_.config()) {
        const auto& c = *store_.config();
        station = "{\"callsign\":" + wtp::json::quote(c.callsign) +
                  ",\"locator\":" + wtp::json::quote(c.locator) +
                  ",\"power_dbm\":" + std::to_string(c.power_dbm) + "}";
        schedules = "[";
        for (const auto& schedule : c.schedules) {
            if (schedules.size() > 1)
                schedules += ',';
            schedules += "{\"period_s\":" + std::to_string(schedule.period_s) +
                         ",\"phase_s\":" + std::to_string(schedule.phase_s) + "}";
        }
        schedules += ']';
    }
    return "{\"ok\":true,\"configured\":" + std::string(store_.config() ? "true" : "false") +
           ",\"enabled\":" + (store_.config() && store_.config()->enabled ? "true" : "false") +
           ",\"allow_unqualified_frequency\":" +
           (store_.config() && store_.config()->allow_unqualified_frequency ? "true" : "false") +
           ",\"allow_non_amateur_frequency\":" +
           (store_.config() && store_.config()->allow_non_amateur_frequency ? "true" : "false") +
           ",\"gpio_drive_ma\":" +
           std::to_string(store_.config() ? store_.config()->gpio_drive_ma
                                          : factory_config().gpio_drive_ma) +
           ",\"boot_gpio_drive_ma\":" + std::to_string(active_gpio_drive_ma_) +
           ",\"suspended\":" + (suspended_ ? "true" : "false") + ",\"expires_utc_s\":" +
           std::to_string(store_.config() ? store_.config()->expires_utc_s : 0) +
           ",\"owner_id\":" + (s.owner_id ? wtp::json::quote(*s.owner_id) : "null") +
           ",\"job_id\":" + (s.job_id ? wtp::json::quote(*s.job_id) : "null") +
           ",\"boot_id\":" + wtp::json::quote(s.boot_id) + ",\"utc_now_ns\":\"" +
           std::to_string(clock.utc_now_ns) + "\"" + ",\"monotonic_now_ns\":\"" +
           std::to_string(clock.monotonic_now_ns) + "\"" + ",\"sync_age_ns\":\"" +
           std::to_string(clock.sync_age_ns) + "\"" + ",\"station\":" + station +
           ",\"schedules\":" + schedules + ",\"schedule_dial_frequency_nhz\":" +
           (store_.config() && store_.config()->wspr_dial_frequency_hz
                ? wtp::json::quote(
                      std::to_string(std::uint64_t{*store_.config()->wspr_dial_frequency_hz} * ns))
                : "null") +
           ",\"frequency_required\":" +
           (store_.config() && store_.config()->wspr_dial_frequency_hz ? "false" : "true") +
           ",\"engine\":" + wtp::json::quote(service_.config().capability_engine) +
           ",\"storage_healthy\":" + (store_.healthy() ? "true" : "false") +
           ",\"reboot_required\":" + (reboot_required_ ? "true" : "false") +
           ",\"watermark_utc_ns\":\"" + std::to_string(store_.watermark()) +
           "\",\"clock_state\":\"" +
           (clock.state == wtp::ClockState::Synchronized ? "synchronized"
            : clock.state == wtp::ClockState::Holdover   ? "holdover"
                                                         : "unsynchronized") +
           "\",\"uncertainty_ns\":\"" + std::to_string(clock.uncertainty_ns) + "\",\"state\":\"" +
           wtp::state_name(s.state) + "\",\"last_error\":" +
           (last_error_ == wtp::ErrorCode::None ? "null" : wtp::error_json(last_error_)) +
           ",\"last_job\":\"" + last_job_ + "\",\"wspr_frame\":" + std::to_string(last_frame_) +
           ",\"wspr_frames\":" + std::to_string(last_frame_count_) +
           ",\"wspr_pair_pending\":" + (pair_ ? "true" : "false") +
           ",\"output_active\":" + (s.output_active ? "true" : "false") + "}\n";
}
std::string Scheduler::command(std::string_view line) {
    if (line == "STATUS")
        return status();
    if (line == "STORAGE")
        return "{\"ok\":true,\"healthy\":" + std::string(store_.healthy() ? "true" : "false") +
               ",\"config\":{\"sequence\":\"" + std::to_string(store_.config_sequence()) +
               "\",\"latest_offset\":" + std::to_string(store_.config_offset()) +
               ",\"record_size\":" + std::to_string(store_.config_record_size()) +
               "},\"watermark\":{\"sequence\":\"" + std::to_string(store_.cursor_sequence()) +
               "\",\"latest_offset\":" + std::to_string(store_.cursor_offset()) +
               ",\"record_size\":" + std::to_string(store_.cursor_record_size()) + "}}\n";
    if (line == "STOP") {
        suspended_ = true;
        pair_.reset();
        const auto current = service_.status();
        if (current.owner_id) {
            if (*current.owner_id != local_id || !current.job_id ||
                (*current.job_id != last_job_ && current.job_id != message_job_))
                return error("external_owner");
            if (current.state == wtp::State::Armed || current.state == wtp::State::Running ||
                current.state == wtp::State::Loaded) {
                const auto result = request("ABORT", wtp::AbortBody{*current.job_id});
                if (!result.ok)
                    return error("stop_failed");
            }
            (void)request("RELEASE");
        }
        if (!idle())
            return error("not_idle");
        return status();
    }
    if (!line.starts_with("CONFIG "))
        return error("unknown_command");
    if (!idle())
        return error("busy");
    auto config = parse_config(line.substr(7));
    if (!config)
        return error("invalid_config");
    const auto supplied = wtp::json::parse(line.substr(7));
    if (!store_.config() && supplied) {
        const auto defaults = factory_config();
        if (!supplied->get("gpio_drive_ma"))
            config->gpio_drive_ma = defaults.gpio_drive_ma;
        if (!supplied->get("pins"))
            config->pins = defaults.pins;
        else if (!supplied->get("pins")->get("amplifier_active_high"))
            config->pins.amplifier_active_high = defaults.pins.amplifier_active_high;
        if (!supplied->get("wspr_dial_frequency_hz"))
            config->wspr_dial_frequency_hz = defaults.wspr_dial_frequency_hz;
    }
    if (store_.config() && supplied) {
        if (!supplied->get("manual_correction_ppb"))
            config->manual_correction_ppb = store_.config()->manual_correction_ppb;
        if (!supplied->get("ntp_rf_calibration"))
            config->ntp_rf_calibration = store_.config()->ntp_rf_calibration;
        if (!supplied->get("wspr_dial_frequency_hz"))
            config->wspr_dial_frequency_hz = store_.config()->wspr_dial_frequency_hz;
        if (!supplied->get("amplifier_timing"))
            config->amplifier_timing = store_.config()->amplifier_timing;
        if (!supplied->get("ntp_timeout_s"))
            config->ntp_timeout_s = store_.config()->ntp_timeout_s;
    }
    if (supplied->get("wspr_dial_frequency_hz") &&
        (!store_.config() ||
         config->wspr_dial_frequency_hz != store_.config()->wspr_dial_frequency_hz) &&
        !wspr_frequency_allowed(*config, service_.config().minimum_frequency_nhz,
                                service_.config().maximum_frequency_nhz))
        return error("frequency_not_allowed");
    if (config->wspr_dial_frequency_hz &&
        (!store_.config() || !store_.config()->wspr_dial_frequency_hz))
        config->enabled = false; // First Console selection also requires deliberate enablement.
    if (config->enabled && !config->wspr_dial_frequency_hz)
        return error("standalone_frequency_required");
    if (config->enabled && message_recovery_required())
        return error("message_recovery_required");
    if (const auto conflict = hardware::validate_filters(store_.filters(), config->pins);
        !conflict.empty())
        return error(conflict);
    if (!store_.config_fits(*config))
        return error("saved_settings_too_large");
    if (config->enabled && store_.message_schedule() && store_.message_schedule()->enabled)
        return error("message_schedule_enabled");
    if (!store_.save(*config))
        return error("storage_fault");
    // The scheduler reads station/schedules from Store on each new job. Only
    // network and pin settings are boot-initialized. Compare with the active boot, not
    // the previous save: a later station edit cannot conceal a pending change.
    if (active_pins_ != config->pins || active_gpio_drive_ma_ != config->gpio_drive_ma ||
        active_amplifier_timing_ != config->amplifier_timing) {
        pin_restart_required_ = true;
        reboot_required_ = true;
        if (!service_.local_inhibit_output()) {
            hardware_application_failed_ = true;
            return error("output_disable_failed");
        }
    }
    reboot_required_ = external_network_restart_required_ || pin_restart_required_ ||
                       active_ntp_timeout_s_ != config->ntp_timeout_s || !active_network_ ||
                       *active_network_ != network_digest(*config);
    return status();
}
std::string Scheduler::save_filters(const hardware::FilterSettings& settings) {
    if (!idle())
        return "busy";
    if (const auto error = hardware::validate_filters(
            settings, store_.config() ? store_.config()->pins : hardware::PinPlan{});
        !error.empty())
        return error;
    if (!store_.save_filters(settings))
        return store_.healthy() ? "saved_settings_too_large" : "storage_fault";
    if (active_filters_ != settings) {
        pin_restart_required_ = reboot_required_ = true;
        if (!service_.local_inhibit_output()) {
            hardware_application_failed_ = true;
            return "output_disable_failed";
        }
    }
    return {};
}
} // namespace wsprrypico::standalone
