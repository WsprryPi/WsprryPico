#include "standalone/scheduler.hpp"

#include "encoding/wspr.hpp"
#include "time/sntp.hpp"
#include "wtp/codec.hpp"

#include <algorithm>
#include <cstdio>
#include <limits>

namespace wsprrypico::standalone {
namespace {
constexpr std::uint64_t ns = 1'000'000'000ULL;
constexpr std::uint64_t frequency = 3'570'100'000'000'000ULL, spacing = 1'464'843'750ULL;
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
} // namespace
Scheduler::Scheduler(Store& store, wtp::JobService& service) : store_(store), service_(service) {
    if (store_.config())
        active_network_ = network_digest(*store_.config());
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
    return service_.handle(r);
}
bool Scheduler::idle() const {
    const auto s = service_.status();
    return !s.owner_id && !s.output_active && s.state != wtp::State::Armed &&
           s.state != wtp::State::Running && s.state != wtp::State::Failed;
}
bool Scheduler::reset_permitted() const {
    if (idle())
        return true;
    const auto s = service_.status();
    // Explicit Console reset can recover a latched fault only without an owner,
    // RF output, or an enabled autonomous schedule. The caller must still verify
    // engine disable before actually resetting; this does not clear WTP state.
    return s.state == wtp::State::Failed && !s.owner_id && !s.output_active && store_.healthy() &&
           store_.config() && !store_.config()->enabled;
}
void Scheduler::poll() {
    service_.poll();
    if (!store_.healthy() || !store_.config() || !store_.config()->enabled || reboot_required_ ||
        suspended_ || !idle())
        return;
    const auto now = service_.clock_snapshot();
    if (now.state == wtp::ClockState::Unsynchronized || now.leap != wtp::LeapState::Normal ||
        now.uncertainty_ns > service_.config().maximum_arm_uncertainty_ns ||
        (now.state == wtp::ClockState::Holdover &&
         (!service_.config().maximum_holdover_age_ns ||
          now.sync_age_ns > service_.config().maximum_holdover_age_ns)) ||
        now.utc_now_ns < time::sntp_min_utc_ns || now.utc_now_ns >= time::sntp_max_utc_ns)
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
    const auto expiry = store_.config()->expires_utc_s * ns;
    if (expiry && (candidate >= expiry || expiry - candidate < 110'592'000'000ULL))
        return;
    if (!request("HELLO", wtp::HelloBody{{"WTP/1"}}).ok)
        return;
    auto response = request("CLAIM", wtp::ClaimBody{local_id, 5000});
    if (!response.ok) {
        last_error_ = response.error;
        return;
    }
    // Durable at-most-once reservation BEFORE preparation/arming. A failure
    // after this point skips the occurrence; it never retries an ambiguous job.
    if (!store_.reserve(candidate)) {
        (void)request("RELEASE");
        return;
    }
    const auto& c = *store_.config();
    auto symbols = encoding::wspr_type1(c.callsign, c.locator, c.power_dbm);
    if (!symbols) {
        (void)request("RELEASE");
        return;
    }
    wtp::Job job{id(candidate), "rf-events/1", "wspr", 110'592'000'000ULL, {}, true};
    job.events.reserve(162);
    for (unsigned i = 0; i < symbols->size(); ++i) {
        const auto start = (std::uint64_t{i} * 2'048'000'000ULL + 1) / 3;
        const auto end = (std::uint64_t{i + 1} * 2'048'000'000ULL + 1) / 3;
        job.events.push_back({start, end - start, true, frequency + (*symbols)[i] * spacing});
    }
    last_job_ = job.job_id;
    response = request("LOAD", std::move(job));
    if (response.ok)
        response = request("ARM", wtp::ArmBody{last_job_, candidate,
                                               service_.config().maximum_arm_uncertainty_ns});
    last_error_ = response.error;
    if (!response.ok)
        (void)request("RELEASE");
}
std::string Scheduler::status() const {
    const auto s = service_.status();
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
           ",\"suspended\":" + (suspended_ ? "true" : "false") + ",\"expires_utc_s\":" +
           std::to_string(store_.config() ? store_.config()->expires_utc_s : 0) +
           ",\"boot_id\":" + wtp::json::quote(s.boot_id) + ",\"utc_now_ns\":\"" +
           std::to_string(clock.utc_now_ns) + "\"" + ",\"monotonic_now_ns\":\"" +
           std::to_string(clock.monotonic_now_ns) + "\"" + ",\"sync_age_ns\":\"" +
           std::to_string(clock.sync_age_ns) + "\"" + ",\"station\":" + station +
           ",\"schedules\":" + schedules +
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
           ",\"last_job\":\"" + last_job_ +
           "\",\"output_active\":" + (s.output_active ? "true" : "false") + "}\n";
}
std::string Scheduler::command(std::string_view line) {
    if (line == "STATUS")
        return status();
    if (line == "STOP") {
        suspended_ = true;
        const auto current = service_.status();
        if (current.owner_id) {
            if (*current.owner_id != local_id || !current.job_id || *current.job_id != last_job_)
                return error("external_owner");
            if (current.state == wtp::State::Armed || current.state == wtp::State::Running ||
                current.state == wtp::State::Loaded) {
                const auto result = request("ABORT", wtp::AbortBody{last_job_});
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
    if (!store_.save(*config))
        return error("storage_fault");
    // The scheduler reads station/schedules from Store on each new job. Only
    // network settings are boot-initialized. Compare with the active boot, not
    // the previous save: a later station edit cannot conceal a pending change.
    reboot_required_ = !active_network_ || *active_network_ != network_digest(*config);
    return status();
}
} // namespace wsprrypico::standalone
