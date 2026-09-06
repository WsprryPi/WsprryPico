#include "time/sntp.hpp"

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
    if (!pending_ || packet.size() != 48 || now < sent_ || now - sent_ > 1'000'000'000ULL ||
        (packet[0] & 7) != 4 || ((packet[0] >> 3) & 7) != 4 ||
        read(packet.subspan(24, 8)) != nonce_)
        return false;
    pending_ = false;
    if (packet[1] == 0) { // Conservatively stop this server for the boot on any KoD.
        denied_ = true;
        clock_.invalidate();
        return false;
    }
    if ((packet[0] >> 6) != 0 || packet[1] > 15) {
        clock_.invalidate(); // Pending/unknown leap requires a richer source; fail closed.
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
    const auto estimate = sent + (elapsed - (sent - received)) / 2;
    if (estimate >= sntp_max_utc_ns || uncertainty > 20'000'000ULL)
        return false;
    // Keep the UTC-to-monotonic offset on the RP2350's microsecond grid.
    // The added 999 ns uncertainty covers flooring this offset, so exact UTC
    // slot requests map to representable local alarm times.
    const auto fraction = (estimate % 1000 + 1000 - now % 1000) % 1000;
    return clock_.observe(estimate - fraction, now, uncertainty, wtp::LeapState::Normal);
}
} // namespace wsprrypico::time
