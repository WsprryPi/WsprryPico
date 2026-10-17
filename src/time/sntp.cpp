#include "time/sntp.hpp"

#include "wtp/json.hpp"

namespace wsprrypico::time {
namespace {
std::uint64_t read(std::span<const std::uint8_t> bytes) {
    std::uint64_t n = 0;
    for (auto byte : bytes)
        n = (n << 8) | byte;
    return n;
}
std::uint64_t timestamp(std::span<const std::uint8_t> bytes) {
    auto seconds = read(bytes.first(4));
    // Fixed era window: 2025 through 2099 spans exactly one NTP wrap.
    if (seconds < 2'208'988'800ULL)
        seconds += 1ULL << 32;
    return (seconds - 2'208'988'800ULL) * 1'000'000'000ULL +
           ((read(bytes.last(4)) * 1'000'000'000ULL) >> 32);
}
} // namespace
std::array<std::uint8_t, 48> Sntp::request(std::uint64_t now, std::uint64_t nonce) {
    std::array<std::uint8_t, 48> packet{};
    packet[0] = 0x23; // LI=0, VN=4, client mode.
    packet[2] = 6;    // 64-second poll.
    packet[3] = 0xec; // Nominal local timestamp precision, not an accuracy claim.
    sent_ = now;
    nonce_ = nonce ? nonce : 1;
    pending_ = !denied_;
    for (unsigned i = 0; i < 8; ++i)
        packet[40 + i] = static_cast<std::uint8_t>(nonce_ >> ((7 - i) * 8));
    return packet;
}
bool Sntp::receive(std::span<const std::uint8_t> packet, std::uint64_t now) {
    packet_accepted_ = arbiter_selected_ = false;
    reason_ = "packet_rejected";
    if (!pending_ || packet.size() != 48 || now < sent_ || now - sent_ > 1'000'000'000ULL ||
        (packet[0] & 7) != 4 || ((packet[0] >> 3) & 7) != 4 ||
        read(packet.subspan(24, 8)) != nonce_)
        return false;
    pending_ = false;
    last_rtt_ns_ = now - sent_;
    last_uncertainty_ns_.reset();
    if (packet[1] == 0) { // Conservatively stop this server for the boot on any KoD.
        denied_ = true;
        filter_.reset();
        selected_.reset();
        applied_id_ = 0;
        reason_ = "kiss_of_death";
        clock_.invalidate(ObservationSource::Sntp);
        return false;
    }
    if ((packet[0] >> 6) != 0 || packet[1] > 15) {
        filter_.reset();
        selected_.reset();
        applied_id_ = 0;
        reason_ = "leap_or_stratum";
        clock_.invalidate(
            ObservationSource::Sntp); // Pending/unknown leap requires a richer source; fail closed.
        return false;
    }
    const auto precision = static_cast<std::int8_t>(packet[3]);
    if (precision > -10 || precision < -40)
        return false;
    if (!read(packet.subspan(16, 8)) || !read(packet.subspan(32, 8)) ||
        !read(packet.subspan(40, 8)))
        return false;
    const auto reference = timestamp(packet.subspan(16, 8));
    const auto received = timestamp(packet.subspan(32, 8));
    const auto sent = timestamp(packet.subspan(40, 8));
    const auto elapsed = now - sent_;
    if (received < sntp_min_utc_ns || sent >= sntp_max_utc_ns || sent < received ||
        reference > sent || sent - reference > 86'400'000'000'000ULL || sent - received > elapsed)
        return false;
    const auto root_delay = read(packet.subspan(4, 4));
    const auto dispersion = read(packet.subspan(8, 4));
    if (root_delay & 0x80000000ULL)
        return false; // Reject negative signed 16.16 delay.
    // Full local RTT is conservative for unknown path asymmetry; include the
    // server's root distance, oscillator growth in flight and 1 ms local margin.
    const auto uncertainty = elapsed + ((root_delay * 1'000'000'000ULL) >> 17) +
                             ((dispersion * 1'000'000'000ULL) >> 16) + 1'050'999ULL;
    last_uncertainty_ns_ = uncertainty;
    const auto estimate = sent + (elapsed - (sent - received)) / 2;
    if (estimate >= sntp_max_utc_ns || uncertainty > standalone_max_uncertainty_ns)
        return false;
    // Keep the UTC-to-monotonic offset on the RP2350's microsecond grid.
    // The added 999 ns uncertainty covers flooring this offset, so exact UTC
    // slot requests map to representable local alarm times.
    const auto fraction = (estimate % 1000 + 1000 - now % 1000) % 1000;
    NtpSample sample{++observation_id_,
                     epoch_,
                     sent_,
                     now,
                     estimate - fraction,
                     uncertainty,
                     elapsed,
                     reference,
                     received,
                     sent,
                     std::uint32_t(root_delay),
                     std::uint32_t(dispersion),
                     packet[1],
                     std::uint8_t(packet[0] >> 6),
                     precision};
    last_sample_ = sample;
    packet_accepted_ = filter_.add(sample);
    if (!packet_accepted_) {
        reason_ = "duplicate_or_invalid_sample";
        return false;
    }
    selected_ = filter_.selected(now);
    reason_ = "packet_accepted_filter_retained";
    if (!selected_ || selected_->id <= applied_id_)
        return true; // Original anchor age remains unchanged; never refresh an old sample.
    const auto fitted = filter_.rate(now);
    arbiter_selected_ =
        clock_.observe_rate(selected_->utc_ns, selected_->raw_ns, selected_->uncertainty_ns,
                            fitted.qualified ? fitted.utc_rate_ppb : 0,
                            fitted.qualified ? fitted.uncertainty_ppb : 0, filter_.generation());
    reason_ = arbiter_selected_ ? "arbiter_accepted" : "arbiter_rejected";
    if (arbiter_selected_)
        applied_id_ = selected_->id;
    else {
        filter_.reset(); // Disagreement/controller transitions cannot seed a later fit.
        selected_.reset();
        applied_id_ = 0;
    }
    return true;
}
std::string Sntp::observations_json() const {
    return "{\"source\":\"sntp\",\"packet_accepted\":" +
           std::string(packet_accepted_ ? "true" : "false") +
           ",\"reason\":" + wtp::json::quote(reason_) + ",\"last_accepted_measurement\":" +
           (last_sample_ ? sample_json(*last_sample_) : "null") +
           ",\"filter_selected\":" + (selected_ ? sample_json(*selected_) : "null") +
           ",\"arbiter_accepted_this_packet\":" + (arbiter_selected_ ? "true" : "false") +
           ",\"anchor_observation_id\":\"" + std::to_string(applied_id_) + "\"}";
}
} // namespace wsprrypico::time
