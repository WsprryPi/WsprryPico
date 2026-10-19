// SPDX-License-Identifier: MIT
#include "time/clock_probe.hpp"

#include "time/mapping.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <charconv>

namespace wsprrypico::time {
namespace {
using wtp::json::quote;
std::string ns(std::uint64_t value) {
    return quote(std::to_string(value));
}
std::string boolean(bool value) {
    return value ? "true" : "false";
}
std::string error(std::string_view name) {
    return "{\"ok\":false,\"error\":" + quote(name) + "}\n";
}
std::string identity(ClockProbeBinding b) {
    return "\"schema\":\"pico-clock-probe/1\",\"device_id\":" + quote(b.device) +
           ",\"boot_id\":" + quote(b.boot) + ",\"firmware\":" + quote(b.firmware) +
           ",\"revision\":" + quote(b.revision) + ",\"gpio\":22";
}
std::string snapshot(const wtp::ClockSnapshot& c) {
    constexpr std::array states{"unsynchronized", "synchronized", "holdover"};
    constexpr std::array leaps{"normal", "insert_pending", "delete_pending", "unknown"};
    return "{\"state\":" + quote(states[static_cast<unsigned>(c.state)]) +
           ",\"utc_now_ns\":" + ns(c.utc_now_ns) +
           ",\"monotonic_now_ns\":" + ns(c.monotonic_now_ns) +
           ",\"uncertainty_ns\":" + ns(c.uncertainty_ns) + ",\"sync_age_ns\":" + ns(c.sync_age_ns) +
           ",\"leap\":" + quote(leaps[static_cast<unsigned>(c.leap)]) +
           ",\"rate_ppb\":" + std::to_string(c.rate_ppb) +
           ",\"rate_uncertainty_ppb\":" + std::to_string(c.rate_uncertainty_ppb) +
           ",\"model_generation\":" + ns(c.model_generation) +
           ",\"rate_until_monotonic_ns\":" + ns(c.rate_until_monotonic_ns) +
           ",\"subsequent_rate_ppb\":" + std::to_string(c.subsequent_rate_ppb) + "}";
}
} // namespace
bool bind_probe_edge(ClockProbeRecord& record, const wtp::ClockSnapshot& before,
                     const wtp::ClockSnapshot& after, std::uint64_t lower, std::uint64_t upper) {
    record.rise_before = before;
    record.rise_after = after;
    const auto at = [&](std::uint64_t raw, wtp::ClockSnapshot& result) {
        result = before;
        result.monotonic_now_ns = raw;
        if (raw < before.monotonic_now_ns ||
            raw - before.monotonic_now_ns > UINT64_MAX - before.sync_age_ns ||
            !project(before, raw, result.utc_now_ns))
            return false;
        result.sync_age_ns = before.sync_age_ns + raw - before.monotonic_now_ns;
        result.uncertainty_ns = std::max(before.uncertainty_ns, after.uncertainty_ns);
        if (raw >= before.rate_until_monotonic_ns) {
            result.rate_ppb = before.subsequent_rate_ppb;
            result.rate_until_monotonic_ns = UINT64_MAX;
        }
        return true;
    };
    if (lower > upper || lower < before.monotonic_now_ns || upper > after.monotonic_now_ns ||
        before.model_generation != after.model_generation || before.state != after.state ||
        before.leap != after.leap || !at(lower, record.rise_before) ||
        !at(upper, record.rise_after)) {
        record.rise_before.state = record.rise_after.state = wtp::ClockState::Unsynchronized;
        record.rise_before.monotonic_now_ns = lower;
        record.rise_after.monotonic_now_ns = upper;
        record.rise_before.utc_now_ns = record.rise_after.utc_now_ns = 0;
        return false;
    }
    return true;
}
std::string ClockProbe::record_json(ClockProbeBinding binding) const {
    const auto& r = *last_;
    const auto& a = r.rise_before;
    const auto& b = r.rise_after;
    // time_us_64() floors to a microsecond. The upper physical-edge bound
    // includes a full timer quantum, then projects through the same UTC model.
    std::uint64_t upper_utc = 0;
    const bool bounded = b.monotonic_now_ns <= UINT64_MAX - raw_resolution_ns &&
                         project(b, b.monotonic_now_ns + raw_resolution_ns, upper_utc);
    const bool hardware_ok = r.high_readback && r.low_readback && r.restored;
    const bool clock_valid =
        hardware_ok && bounded && r.source_sntp && !r.disagreement &&
        a.state == wtp::ClockState::Synchronized && a.state == b.state &&
        a.leap == wtp::LeapState::Normal && a.leap == b.leap && a.model_generation &&
        a.model_generation == b.model_generation && b.monotonic_now_ns >= a.monotonic_now_ns &&
        b.monotonic_now_ns - a.monotonic_now_ns + raw_resolution_ns <= maximum_edge_bracket_ns &&
        b.utc_now_ns >= a.utc_now_ns;
    return "{\"ok\":" + boolean(hardware_ok) + "," + identity(binding) +
           ",\"sequence\":" + ns(r.sequence) + ",\"clock_valid\":" + boolean(clock_valid) +
           ",\"source_sntp\":" + boolean(r.source_sntp) +
           ",\"source_disagreement\":" + boolean(r.disagreement) +
           ",\"rise_before\":" + snapshot(a) + ",\"rise_after\":" + snapshot(b) +
           ",\"raw_resolution_ns\":1000,\"rise_raw_lower_ns\":" + ns(a.monotonic_now_ns) +
           ",\"rise_raw_upper_ns\":" +
           (bounded ? ns(b.monotonic_now_ns + raw_resolution_ns) : "null") +
           ",\"rise_utc_lower_ns\":" + ns(a.utc_now_ns) +
           ",\"rise_utc_upper_ns\":" + (bounded ? ns(upper_utc) : "null") +
           ",\"fall_before_ns\":" + ns(r.fall_before_ns) +
           ",\"fall_after_ns\":" + ns(r.fall_after_ns) +
           ",\"requested_width_us\":1000,\"high_readback\":" + boolean(r.high_readback) +
           ",\"low_readback\":" + boolean(r.low_readback) +
           ",\"pin_restored\":" + boolean(r.restored) +
           ",\"ntp_generation\":" + ns(r.ntp_generation) +
           ",\"source_epoch\":" + ns(r.source_epoch) + ",\"source_raw_ns\":" + ns(r.source_raw_ns) +
           ",\"frequency_ppb\":" + std::to_string(r.frequency_ppb) +
           ",\"frequency_uncertainty_ppb\":" + std::to_string(r.frequency_uncertainty_ppb) +
           (hardware_ok ? "}\n" : ",\"error\":\"pulse_hardware_fault\"}\n");
}
std::string ClockProbe::command(std::string_view request, ClockProbeBinding b,
                                const ClockProbeGuard& guard, std::uint64_t now,
                                ClockProbeHardware& hardware) {
    // Fixed token count, canonical spaces and integer syntax. No heap-backed
    // command queue, periodic output, configuration writes or time submission.
    std::array<std::string_view, 4> fields{};
    std::size_t count = 0;
    while (!request.empty() && count < fields.size()) {
        const auto split = request.find(' ');
        fields[count++] = request.substr(0, split);
        if (fields[count - 1].empty())
            return error("clock_probe_command");
        if (split == request.npos) {
            request = {};
            break;
        }
        request.remove_prefix(split + 1);
        if (request.empty())
            return error("clock_probe_command");
    }
    if (!request.empty() || count < 3)
        return error("clock_probe_command");
    if (fields[0] != b.device || fields[1] != b.boot)
        return error("clock_probe_identity");
    if (count == 3 && fields[2] == "STATUS") {
        auto cached = last_ ? record_json(b) : "null";
        if (last_)
            cached.pop_back();
        return "{\"ok\":true," + identity(b) + ",\"last_sequence\":" + ns(sequence_) +
               ",\"maximum_pulses\":4096,\"minimum_interval_ns\":\"500000000\","
               "\"requested_width_us\":1000,\"last_record\":" +
               cached + "}\n";
    }
    if (count == 3 && fields[2] == "READ") {
        if (!guard.permitted)
            return error("clock_probe_busy");
        const auto input = hardware.read();
        if (!input)
            return error("clock_probe_pin_fault");
        return "{\"ok\":true," + identity(b) + ",\"level\":" + boolean(input->level) +
               ",\"output_enabled\":" + boolean(input->output_enabled) +
               ",\"pad_before\":" + std::to_string(input->pad_before) +
               ",\"pad_settling\":" + std::to_string(input->pad_settling) +
               ",\"pad_sampling\":" + std::to_string(input->pad_sampling) +
               ",\"control_sampling\":" + std::to_string(input->control_sampling) +
               ",\"settle_us\":" + std::to_string(input->settle_us) +
               ",\"raw_before_ns\":" + ns(input->raw_before_ns) +
               ",\"raw_after_ns\":" + ns(input->raw_after_ns) + "}\n";
    }
    std::uint64_t sequence = 0;
    if (count != 4 || fields[2] != "PULSE" || fields[3].empty() || fields[3].front() == '0')
        return error("clock_probe_command");
    const auto parsed =
        std::from_chars(fields[3].data(), fields[3].data() + fields[3].size(), sequence);
    if (parsed.ec != std::errc{} || parsed.ptr != fields[3].data() + fields[3].size())
        return error("clock_probe_command");
    if (last_ && sequence == sequence_)
        return record_json(b); // Lost replies never produce a second edge.
    if (sequence_ >= maximum_pulses || sequence != sequence_ + 1)
        return error("clock_probe_sequence");
    if (!guard.permitted)
        return error("clock_probe_busy");
    if (sequence_ && (now < last_attempt_ns_ || now - last_attempt_ns_ < minimum_interval_ns))
        return error("clock_probe_rate_limited");
    // Consume before touching hardware: a partial/failed physical attempt must
    // be retrieved, never ambiguously replayed as another pulse.
    sequence_ = sequence;
    last_attempt_ns_ = now;
    last_.emplace();
    auto& record = *last_;
    record.sequence = sequence;
    record.ntp_generation = guard.ntp_generation;
    record.source_epoch = guard.source_epoch;
    record.source_raw_ns = guard.source_raw_ns;
    record.frequency_ppb = guard.frequency_ppb;
    record.frequency_uncertainty_ppb = guard.frequency_uncertainty_ppb;
    record.source_sntp = guard.source_sntp;
    record.disagreement = guard.disagreement;
    hardware.pulse(record);
    return record_json(b);
}
} // namespace wsprrypico::time
