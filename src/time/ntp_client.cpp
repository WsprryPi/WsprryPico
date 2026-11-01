#include "time/ntp_client.hpp"

#include "time/mapping.hpp"
#include "wtp/json.hpp"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>

namespace wsprrypico::time {
namespace {
microchrony::Config pico_config() {
    microchrony::Config config;
    config.max_drift_ppm = 100;      // Supported Pico oscillator range, separate from phase slew.
    config.max_clock_error_ppm = 50; // Existing conservative Pico holdover drift allowance.
    config.max_poll =
        config.min_poll; // Routine polling stays at 64 seconds; outage policy is separate.
    return config;
}
std::uint64_t ns(double seconds) {
    return !(seconds >= 0) || seconds >= double(UINT64_MAX) / 1e9
               ? UINT64_MAX
               : std::uint64_t(std::ceil(seconds * 1e9));
}
std::uint64_t magnitude(std::int64_t value) {
    return value < 0 ? std::uint64_t(-(value + 1)) + 1 : std::uint64_t(value);
}
} // namespace
NtpClient::NtpClient(ObservationSink& clock) : clock_(clock), core_(pico_config()) {
    (void)core_.configure(0, 1, 0);
}
bool NtpClient::configure(unsigned slot, std::uint32_t endpoint, std::uint64_t now) {
    if (slot >= epochs_.size())
        return false;
    const bool changed = core_.status(slot, now).endpoint != endpoint;
    if (!core_.configure(slot, endpoint, now))
        return false;
    if (changed) {
        ++epochs_[slot];
        request_ns_[slot] = request_tokens_[slot] = 0;
    }
    return true;
}
void NtpClient::remove(unsigned slot, std::uint64_t now) {
    core_.remove(slot, now);
    if (slot < epochs_.size()) {
        ++epochs_[slot];
        request_ns_[slot] = request_tokens_[slot] = 0;
    }
}
void NtpClient::reset_peer(bool invalidate_clock) {
    core_.reset(last_now_);
    for (auto& epoch : epochs_)
        ++epoch;
    request_ns_.fill(0);
    request_tokens_.fill(0);
    packet_accepted_ = arbiter_selected_ = false;
    control_ = {};
    if (invalidate_clock)
        clock_.invalidate(ObservationSource::Sntp);
}
void NtpClient::cancel(unsigned slot) {
    core_.cancel(slot);
}
void NtpClient::seed_rate(std::int32_t rate, std::uint32_t skew) {
    core_.seed(rate, skew);
}
void NtpClient::clear_seed() {
    core_.seed(0);
    reset_peer();
}
std::optional<std::array<std::uint8_t, 48>>
NtpClient::scheduled_request(unsigned slot, std::uint64_t now, std::uint64_t token) {
    last_now_ = now;
    auto result = core_.request(slot, now, token);
    if (result) {
        request_ns_[slot] = now;
        request_tokens_[slot] = token ? token : 1;
    }
    return result;
}
std::array<std::uint8_t, 48> NtpClient::request(std::uint64_t now, std::uint64_t token) {
    last_now_ = now;
    auto result = core_.request(0, now, token, true);
    if (result) {
        request_ns_[0] = now;
        request_tokens_[0] = token ? token : 1;
    }
    return result.value_or(std::array<std::uint8_t, 48>{});
}
bool NtpClient::receive(unsigned slot, std::span<const std::uint8_t> packet, std::uint64_t now,
                        bool discipline, std::size_t wire_length) {
    last_now_ = now;
    arbiter_selected_ = false;
    if (slot >= epochs_.size() || packet_sequence_ == UINT64_MAX)
        return false;
    auto& offered = packets_[packet_sequence_++ % packets_.size()];
    offered = {};
    offered.id = packet_sequence_;
    offered.epoch = epochs_[slot];
    offered.slot = slot;
    offered.endpoint = core_.status(slot, now).endpoint;
    offered.send_ns = request_ns_[slot];
    offered.token = request_tokens_[slot];
    offered.receive_ns = now;
    const auto length = wire_length ? wire_length : packet.size();
    offered.length = std::uint32_t(std::min<std::size_t>(length, UINT32_MAX));
    std::copy_n(packet.begin(), std::min({packet.size(), offered.prefix.size(), length}),
                offered.prefix.begin());
    const auto before_generation = core_.tracking(now).generation;
    // A bounded transport prefix can describe an oversized datagram but can
    // never turn it into a valid 48-byte packet at the admission boundary.
    packet_accepted_ = core_.receive(slot, length == packet.size() ? packet : packet.first(0), now);
    offered.accepted = packet_accepted_;
    offered.rejection =
        packet_accepted_ ? microchrony::Rejection::None : core_.status(slot, now).reason;
    if (discipline) {
        const bool applied = apply(now);
        arbiter_selected_ =
            packet_accepted_ && applied && core_.tracking(now).generation != before_generation;
    }
    return packet_accepted_;
}
bool NtpClient::apply(std::uint64_t now) {
    last_now_ = now;
    const auto tracking = core_.tracking(now);
    arbiter_selected_ = false;
    control_ = {};
    if (!tracking.synchronized || tracking.source_raw_ns > now) {
        // Losing a usable NTP estimate is not a new clock observation. Leave
        // the last accepted anchor at its original age; the discipline's
        // configured timeout and growing uncertainty decide its usability.
        return false;
    }
    wtp::ClockSnapshot model;
    model.state = wtp::ClockState::Synchronized;
    model.utc_now_ns = tracking.utc_ns;
    model.monotonic_now_ns = now;
    model.sync_age_ns = now - tracking.source_raw_ns;
    model.uncertainty_ns = tracking.uncertainty_ns;
    model.leap = wtp::LeapState::Normal;
    if (tracking.leap != microchrony::Leap::Normal) {
        using namespace std::chrono;
        const year_month_day date{sys_days{days{tracking.utc_ns / (86'400 * microchrony::second)}}};
        const auto transition = unsigned(date.month()) <= 6
                                    ? sys_days{date.year() / July / 1}
                                    : sys_days{(date.year() + years{1}) / January / 1};
        model.leap_transition_utc_ns =
            std::uint64_t(duration_cast<seconds>(transition.time_since_epoch()).count()) *
            microchrony::second;
        model.leap = tracking.leap == microchrony::Leap::Insert ? wtp::LeapState::InsertPending
                                                                : wtp::LeapState::DeletePending;
    }
    model.rate_ppb = tracking.rate_ppb;
    model.rate_uncertainty_ppb = tracking.skew_ppb;
    model.model_generation = tracking.generation;
    model.subsequent_rate_ppb = tracking.utc_frequency_ppb;
    const auto slew = std::int64_t(tracking.rate_ppb) - tracking.utc_frequency_ppb;
    const auto phase = magnitude(tracking.remaining_correction_ns);
    if (slew && phase) {
        std::uint64_t duration{};
        if (!scale(phase, microchrony::second, magnitude(slew), duration, true) ||
            duration > UINT64_MAX - now)
            return false;
        model.rate_until_monotonic_ns = now + duration;
    }
    // Preserve representable RP2350 local alarm times and charge all rounding.
    const auto rounding = (model.utc_now_ns % 1000 + 1000 - now % 1000) % 1000;
    model.utc_now_ns -= rounding;
    if (model.uncertainty_ns > UINT64_MAX - rounding - 1000)
        return false;
    model.uncertainty_ns += rounding + 1000;
    auto reference_utc = tracking.utc_ns;
    if (tracking.remaining_correction_ns < 0) {
        if (phase > reference_utc)
            return false;
        reference_utc -= phase;
    } else {
        if (phase > UINT64_MAX - reference_utc)
            return false;
        reference_utc += phase;
    }
    std::uint64_t elapsed{};
    if (!elapsed_utc(model.sync_age_ns, tracking.utc_frequency_ppb, elapsed) ||
        elapsed > reference_utc)
        return false;
    const RateObservation source{reference_utc - elapsed,
                                 tracking.source_raw_ns,
                                 ns(tracking.root_delay / 2 + tracking.root_dispersion),
                                 tracking.utc_frequency_ppb,
                                 tracking.skew_ppb,
                                 tracking.generation};
    arbiter_selected_ = clock_.observe_ntp_model(
        source, model, std::uint32_t(std::ceil(core_.config().max_clock_error_ppm * 1000)));
    if (arbiter_selected_) {
        control_ = {model.utc_now_ns,
                    now,
                    model.uncertainty_ns,
                    phase,
                    model.rate_ppb,
                    tracking.utc_frequency_ppb,
                    tracking.skew_ppb,
                    tracking.skew_ppb <= 5000,
                    true};
        if (const auto original = last_sample()) {
            control_.generation = tracking.generation;
            control_.selected_sample_raw_ns = original->raw_ns;
            control_.selected_epoch = original->epoch;
        }
    }
    return arbiter_selected_;
}
unsigned NtpClient::selected_slot(std::uint64_t now) const {
    const auto selected = core_.tracking(now).selected;
    return selected < microchrony::source_capacity ? selected : 0;
}
NtpSample NtpClient::convert(unsigned slot, const microchrony::Measurement& m) const {
    const auto elapsed = m.receive_raw_ns - m.raw_ns;
    std::uint64_t utc = m.utc_ns;
    if (elapsed <= UINT64_MAX - utc)
        utc += elapsed;
    return {m.id,
            epochs_[slot],
            m.send_raw_ns,
            m.receive_raw_ns,
            utc,
            ns(m.root_delay / 2 + m.root_dispersion),
            m.receive_raw_ns - m.send_raw_ns,
            m.server_reference_ns,
            m.server_receive_ns,
            m.server_send_ns,
            m.root_delay_wire,
            m.root_dispersion_wire,
            m.stratum,
            std::uint8_t(m.leap),
            m.precision_log};
}
std::optional<NtpSample> NtpClient::sample(unsigned slot) const {
    const auto samples = core_.history(slot);
    return samples.empty() ? std::nullopt : std::optional(convert(slot, samples.back()));
}
std::optional<NtpSample> NtpClient::last_sample() const {
    return sample(selected_slot(last_now_));
}
bool NtpClient::peer_recent(std::uint64_t now, std::uint64_t age) const {
    const auto source = last_sample();
    return source && now >= source->raw_ns && now - source->raw_ns <= age;
}
bool NtpClient::peer_fresh(std::uint64_t now) const {
    return peer_recent(now, ntp_fresh_ns);
}
bool NtpClient::denied() const {
    return core_.status(selected_slot(last_now_), last_now_).reason ==
           microchrony::Rejection::KissDenied;
}
std::uint64_t NtpClient::last_rtt_ns() const {
    const auto* last = core_.last_measurement(selected_slot(last_now_));
    return last ? last->receive_raw_ns - last->send_raw_ns : 0;
}
std::optional<std::uint64_t> NtpClient::last_uncertainty_ns() const {
    const auto* last = core_.last_measurement(selected_slot(last_now_));
    return last ? std::optional(ns(last->root_delay / 2 + last->root_dispersion)) : std::nullopt;
}
RateEstimate NtpClient::rate(std::uint64_t now) const {
    RateEstimate result;
    const auto tracking = core_.tracking(now);
    const auto status = core_.status(selected_slot(now), now);
    result.generation = tracking.generation;
    result.utc_rate_ppb = tracking.utc_frequency_ppb;
    result.uncertainty_ppb = tracking.skew_ppb;
    const auto samples = core_.history(selected_slot(now));
    result.samples = status.estimate.samples;
    if (!samples.empty()) {
        result.sampled_ns = samples.back().receive_raw_ns;
        result.span_ns = samples.back().raw_ns - samples.front().raw_ns;
    }
    result.qualified = tracking.synchronized && tracking.skew_ppb <= 5000 && result.samples >= 3 &&
                       result.span_ns && now >= result.sampled_ns &&
                       now - result.sampled_ns <= ntp_fresh_ns &&
                       std::abs(std::int64_t(result.utc_rate_ppb)) <= 100'000;
    result.reason = result.qualified ? "microchrony_frequency" : "microchrony_learning";
    return result;
}
std::string NtpClient::learning_json(std::uint64_t now) const {
    const auto t = core_.tracking(now);
    const auto ready = microchrony::readiness(t);
    return "{\"schema\":\"microchrony-status/1\",\"synchronized\":" +
           std::string(t.synchronized ? "true" : "false") +
           ",\"phase_settled\":" + (ready.phase_settled ? "true" : "false") +
           ",\"rate_settled\":" + (ready.rate_settled ? "true" : "false") +
           ",\"utc_frequency_ppb\":" + std::to_string(t.utc_frequency_ppb) +
           ",\"skew_ppb\":" + std::to_string(t.skew_ppb) + ",\"remaining_correction_ns\":\"" +
           std::to_string(t.remaining_correction_ns) + "\",\"clock_error_ns\":\"" +
           std::to_string(t.uncertainty_ns) + "\",\"rate_ppb\":" + std::to_string(t.rate_ppb) +
           ",\"rf_candidate\":" + rate_json(rate(now)) + '}';
}
std::string NtpClient::observations_json() const {
    const auto original = last_sample();
    return "{\"source\":\"microchrony\",\"packet_accepted\":" +
           std::string(packet_accepted_ ? "true" : "false") +
           ",\"arbiter_accepted_this_packet\":" + (arbiter_selected_ ? "true" : "false") +
           ",\"last_accepted_measurement\":" + (original ? sample_json(*original) : "null") + '}';
}
std::string NtpClient::history_page(NtpDiagnosticBinding binding, std::string_view request,
                                    std::uint64_t now) const {
    const auto error = [](std::string_view text) {
        return "{\"ok\":false,\"error\":" + wtp::json::quote(text) + "}\n";
    };
    auto slot = selected_slot(now);
    if (request.starts_with("@")) {
        if (request.size() < 4 || request[1] < '0' || request[1] > '3' || request[2] != ' ')
            return error("ntp_history_source");
        slot = unsigned(request[1] - '0');
        request.remove_prefix(3);
    }
    const auto space = request.find(' ');
    if (space == request.npos)
        return error("ntp_history_request");
    const auto token_text = request.substr(0, space), cursor_text = request.substr(space + 1);
    unsigned cursor{};
    const auto parsed =
        std::from_chars(cursor_text.data(), cursor_text.data() + cursor_text.size(), cursor);
    if (cursor_text.empty() || (cursor_text.size() > 1 && cursor_text.front() == '0') ||
        parsed.ec != std::errc{} || parsed.ptr != cursor_text.data() + cursor_text.size())
        return error("ntp_history_cursor");
    const auto samples = core_.history(slot);
    const auto status = core_.status(slot, now);
    const auto identity =
        "{\"schema\":\"microchrony-history-page/1\",\"device_id\":" +
        wtp::json::quote(binding.device) + ",\"boot_id\":" + wtp::json::quote(binding.boot) +
        ",\"firmware\":" + wtp::json::quote(binding.firmware) +
        ",\"revision\":" + wtp::json::quote(binding.revision) +
        ",\"slot\":" + std::to_string(slot) +
        ",\"endpoint\":" + wtp::json::quote(binding.endpoint) + ",\"clock_epoch\":\"" +
        std::to_string(epochs_[slot]) + "\",\"generation\":\"" + std::to_string(status.generation) +
        "\",\"count\":" + std::to_string(samples.size()) +
        ",\"frequency_ppb\":" + std::to_string(std::llround(status.estimate.rate * 1e9)) +
        ",\"skew_ppb\":" + std::to_string(std::uint64_t(std::ceil(status.estimate.skew * 1e9))) +
        ",\"runs\":" + std::to_string(status.estimate.runs);
    if (identity.size() > 1500)
        return error("ntp_history_identity_bound");
    const auto hash =
        wtp::sha256({reinterpret_cast<const std::uint8_t*>(identity.data()), identity.size()});
    std::string token;
    constexpr char hex[] = "0123456789abcdef";
    for (auto byte : hash) {
        token += hex[byte >> 4];
        token += hex[byte & 15];
    }
    // Staleness precedes bounds checks: peer changes can shorten the history.
    if (token_text != "-" && token_text != token)
        return error("ntp_history_changed");
    if (cursor > samples.size() || (token_text == "-" && cursor))
        return error("ntp_history_cursor");
    auto result = identity + ",\"ok\":true,\"token\":\"" + token + "\",\"observed_raw_ns\":\"" +
                  std::to_string(now) + "\",\"cursor\":" + std::to_string(cursor) +
                  ",\"records\":[";
    unsigned next = cursor;
    while (next < samples.size() && next - cursor < 4) {
        const auto record = (next == cursor ? "" : ",") + sample_json(convert(slot, samples[next]));
        if (result.size() + record.size() + 70 > 4096)
            break;
        result += record;
        ++next;
    }
    result += "],\"next_cursor\":" + std::to_string(next) +
              ",\"more\":" + (next < samples.size() ? "true" : "false") + "}\n";
    return result;
}
std::string NtpClient::packet_page(NtpDiagnosticBinding binding, std::string_view text,
                                   std::uint64_t now) const {
    const auto error = [](const char* code) {
        return "{\"ok\":false,\"error\":" + wtp::json::quote(code) + "}\n";
    };
    std::uint64_t cursor = 0;
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), cursor);
    if (text.empty() || (text.size() > 1 && text.front() == '0') || parsed.ec != std::errc{} ||
        parsed.ptr != text.data() + text.size() || cursor == UINT64_MAX ||
        cursor > packet_sequence_)
        return error("ntp_packet_cursor");
    auto result = "{\"ok\":true,\"schema\":\"microchrony-packet-page/1\",\"device_id\":" +
                  wtp::json::quote(binding.device) +
                  ",\"boot_id\":" + wtp::json::quote(binding.boot) +
                  ",\"firmware\":" + wtp::json::quote(binding.firmware) +
                  ",\"revision\":" + wtp::json::quote(binding.revision);
    if (result.size() > 1500)
        return error("ntp_packet_identity_bound");
    const auto count = std::min<std::uint64_t>(packet_sequence_, packets_.size());
    const auto oldest = packet_sequence_ - count + 1;
    const auto first = std::max(cursor + 1, oldest);
    result += ",\"observed_raw_ns\":\"" + std::to_string(now) + "\",\"last_id\":\"" +
              std::to_string(packet_sequence_) + "\",\"oldest_id\":\"" + std::to_string(oldest) +
              "\",\"overwritten\":\"" + std::to_string(packet_sequence_ - count) +
              "\",\"lost_before\":\"" + std::to_string(first - cursor - 1) + "\",\"records\":[";
    auto next = cursor;
    for (auto id = first; id <= packet_sequence_ && id - first < 4; ++id) {
        const auto& r = packets_[(id - 1) % packets_.size()];
        std::string hex;
        constexpr char digits[] = "0123456789abcdef";
        for (unsigned i = 0; i < std::min<std::size_t>(r.length, r.prefix.size()); ++i) {
            hex += digits[r.prefix[i] >> 4];
            hex += digits[r.prefix[i] & 15];
        }
        result += (id == first ? "" : ",") + std::string("{\"id\":\"") + std::to_string(id) +
                  "\",\"slot\":" + std::to_string(r.slot) + ",\"endpoint\":\"" +
                  std::to_string(r.endpoint) + "\",\"clock_epoch\":\"" + std::to_string(r.epoch) +
                  "\",\"request_raw_ns\":\"" + std::to_string(r.send_ns) +
                  "\",\"receive_raw_ns\":\"" + std::to_string(r.receive_ns) +
                  "\",\"request_token\":\"" + std::to_string(r.token) +
                  "\",\"length\":" + std::to_string(r.length) + ",\"prefix_hex\":\"" + hex +
                  "\",\"truncated\":" + (r.length > r.prefix.size() ? "true" : "false") +
                  ",\"accepted\":" + (r.accepted ? "true" : "false") +
                  ",\"reason\":" + wtp::json::quote(microchrony::name(r.rejection)) + '}';
        next = id;
    }
    result += "],\"next_cursor\":\"" + std::to_string(next) +
              "\",\"more\":" + (next < packet_sequence_ ? "true" : "false") + "}\n";
    return result;
}
} // namespace wsprrypico::time
