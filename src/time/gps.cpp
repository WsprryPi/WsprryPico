// SPDX-License-Identifier: MIT
#include "time/gps.hpp"

#include <algorithm>
#include <chrono>

namespace wsprrypico::time::gps {
namespace {
bool digits(std::string_view text, unsigned& result) {
    if (text.empty() || text.size() > 9)
        return false;
    result = 0;
    for (const char c : text) {
        if (c < '0' || c > '9')
            return false;
        result = result * 10 + unsigned(c - '0');
    }
    return true;
}
int hex(char c) {
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    return -1;
}
std::optional<std::uint64_t> tod(std::string_view text) {
    if (text.size() < 6 || text.size() > 16)
        return {};
    unsigned h = 0, m = 0, s = 0;
    if (!digits(text.substr(0, 2), h) || !digits(text.substr(2, 2), m) ||
        !digits(text.substr(4, 2), s) || h > 23 || m > 59 || s > 59)
        return {};
    std::uint64_t fraction = 0;
    if (text.size() != 6) {
        if (text[6] != '.' || text.size() == 7)
            return {};
        unsigned value = 0;
        if (!digits(text.substr(7), value))
            return {};
        fraction = value;
        for (unsigned i = unsigned(text.size() - 7); i < 9; ++i)
            fraction *= 10;
    }
    return (h * 3600ULL + m * 60ULL + s) * second + fraction;
}
std::optional<std::int32_t> coordinate(std::string_view text, std::string_view direction,
                                       bool latitude) {
    const unsigned width = latitude ? 2 : 3;
    if (text.size() < width + 2 || text.size() > width + 10 || direction.size() != 1 ||
        (latitude ? direction != "N" && direction != "S" : direction != "E" && direction != "W"))
        return {};
    unsigned degree = 0, minute = 0;
    if (!digits(text.substr(0, width), degree) || !digits(text.substr(width, 2), minute) ||
        minute > 59 || degree > (latitude ? 90U : 180U))
        return {};
    std::uint64_t numerator = minute, denominator = 1;
    if (text.size() > width + 2) {
        if (text[width + 2] != '.' || text.size() == width + 3)
            return {};
        unsigned fraction = 0;
        const auto fractional = text.substr(width + 3);
        if (!digits(fractional, fraction))
            return {};
        for (unsigned i = 0; i < fractional.size(); ++i)
            denominator *= 10;
        numerator = minute * denominator + fraction;
    }
    if (degree == (latitude ? 90U : 180U) && numerator)
        return {};
    auto value = std::int64_t(degree) * 10'000'000 +
                 std::int64_t((numerator * 10'000'000 + 30 * denominator) / (60 * denominator));
    if (direction == "S" || direction == "W")
        value = -value;
    return std::int32_t(value);
}
std::optional<Message> parse(std::string_view line, std::uint64_t raw, bool& ignored) {
    if (line.size() < 10 || line.front() != '$' || line[line.size() - 3] != '*')
        return {};
    const auto star = line.size() - 3;
    unsigned checksum = 0;
    for (unsigned i = 1; i < star; ++i)
        checksum ^= unsigned(static_cast<unsigned char>(line[i]));
    const int high = hex(line[star + 1]), low = hex(line[star + 2]);
    if (high < 0 || low < 0 || checksum != unsigned(high * 16 + low))
        return {};
    std::array<std::string_view, 24> fields{};
    unsigned count = 0;
    auto body = line.substr(1, star - 1);
    for (;;) {
        if (count == fields.size())
            return {};
        const auto comma = body.find(',');
        fields[count++] = body.substr(0, comma);
        if (comma == body.npos)
            break;
        body.remove_prefix(comma + 1);
    }
    if (fields[0].size() != 5)
        return {};
    const auto talker = fields[0].substr(0, 2), kind = fields[0].substr(2);
    if (talker != "GP" && talker != "GN" && talker != "GA" && talker != "GL" && talker != "BD")
        return {};
    Message result;
    result.received_raw_ns = raw;
    unsigned lat = 0, lon = 0;
    if (kind == "RMC") {
        if (count < 10 || count > 14 || (fields[2] != "A" && fields[2] != "V"))
            return {};
        const auto time = tod(fields[1]);
        if (!time || fields[9].size() != 6)
            return {};
        unsigned day = 0, month = 0, year = 0;
        if (!digits(fields[9].substr(0, 2), day) || !digits(fields[9].substr(2, 2), month) ||
            !digits(fields[9].substr(4, 2), year))
            return {};
        using namespace std::chrono;
        const year_month_day date{std::chrono::year{int(2000 + year)}, std::chrono::month{month},
                                  std::chrono::day{day}};
        if (!date.ok() || year < 25)
            return {};
        result.utc_ns =
            std::uint64_t(sys_days{date}.time_since_epoch().count()) * 86400ULL * second + *time;
        result.time_valid = fields[2] == "A";
        // Explicit simulator/invalid navigation modes cannot grant time or position.
        if (count >= 13 && !fields[12].empty() && fields[12] != "A" && fields[12] != "D" &&
            fields[12] != "F" && fields[12] != "R" && fields[12] != "P")
            result.time_valid = false;
        lat = 3;
        lon = 5;
        result.position_valid = result.time_valid;
        result.time_valid = result.time_valid && bool(utc_valid_until(*result.utc_ns));
    } else if (kind == "GGA") {
        if (count != 15 || !tod(fields[1]))
            return {};
        unsigned quality = 0;
        if (!digits(fields[6], quality) || quality > 8 || !digits(fields[7], result.satellites) ||
            result.satellites > 99)
            return {};
        result.kind = Message::Kind::Gga;
        result.position_valid =
            quality == 1 || quality == 2 || quality == 3 || quality == 4 || quality == 5;
        lat = 2;
        lon = 4;
    } else {
        ignored = true;
        return {};
    }
    const auto latitude = coordinate(fields[lat], fields[lat + 1], true);
    const auto longitude = coordinate(fields[lon], fields[lon + 1], false);
    if (latitude && longitude && result.position_valid)
        result.position = Position{*latitude, *longitude, raw};
    else
        result.position_valid = false;
    return result;
}
} // namespace
void Parser::lost() {
    size_ = 0;
    carriage_return_ = false;
    ++rejected_;
}
std::optional<Message> Parser::byte(char c, std::uint64_t raw) {
    if (c == '$') {
        if (size_)
            ++rejected_;
        size_ = 1;
        buffer_[0] = c;
        started_ns_ = raw;
        carriage_return_ = false;
        return {};
    }
    if (!size_)
        return {};
    if (raw < started_ns_ || raw - started_ns_ > second || (carriage_return_ && c != '\n')) {
        lost();
        return {};
    }
    if (c == '\r') {
        carriage_return_ = true;
        return {};
    }
    if (c == '\n') {
        bool ignored = false;
        const auto result = parse({buffer_.data(), size_}, started_ns_, ignored);
        size_ = 0;
        carriage_return_ = false;
        if (result)
            ++accepted_;
        else if (!ignored)
            ++rejected_;
        return result;
    }
    if (c < 32 || c > 126 || size_ == buffer_.size()) {
        lost();
        return {};
    }
    buffer_[size_++] = c;
    return {};
}
bool valid(const PairingPolicy& p) {
    return p.qualified && p.utc_second_offset >= -1 && p.utc_second_offset <= 1 &&
           p.minimum_message_delay_ns <= p.maximum_message_delay_ns &&
           p.maximum_message_delay_ns < 2 * second &&
           p.maximum_message_delay_ns - p.minimum_message_delay_ns < second &&
           p.receiver_uncertainty_ns > 0 && p.receiver_uncertainty_ns <= 100'000'000 &&
           p.edge_offset_ns >= -500'000'000 && p.edge_offset_ns <= 500'000'000;
}
void Pairer::lost() {
    pulses_ = {};
    previous_.reset();
    error_ = "capture_lost";
}
bool Pairer::pulse(Pulse p) {
    if (!p.raw_ns || !p.sequence || p.uncertainty_ns > 100'000'000 || p.raw_ns < p.uncertainty_ns ||
        p.raw_ns > UINT64_MAX - p.uncertainty_ns || p.sequence <= last_pulse_sequence_ ||
        p.raw_ns <= last_pulse_raw_ns_) {
        lost();
        error_ = "invalid_pps";
        return false;
    }
    const bool continuous =
        !last_pulse_raw_ns_ || (p.sequence == last_pulse_sequence_ + 1 &&
                                p.raw_ns - last_pulse_raw_ns_ >= second - 1'000'000 &&
                                p.raw_ns - last_pulse_raw_ns_ <= second + 1'000'000);
    last_pulse_raw_ns_ = p.raw_ns;
    last_pulse_sequence_ = p.sequence;
    if (!continuous)
        pulses_ = {};
    for (std::size_t i = pulses_.size() - 1; i; --i)
        pulses_[i] = pulses_[i - 1];
    pulses_[0] = p;
    if (!continuous) {
        previous_.reset();
        error_ = "pps_discontinuity";
        return false;
    }
    return true;
}
std::optional<Pulse> Pairer::preceding_pulse(std::uint64_t started) const {
    // Diagnostic nearest preceding edge, independent of the qualified window.
    // message() selects the UTC label's edge from the complete bounded history.
    for (const auto& pulse : pulses_)
        if (pulse.sequence && pulse.raw_ns <= started && started - pulse.raw_ns < second)
            return pulse;
    return {};
}
std::optional<Observation> Pairer::message(const Message& m) {
    if (!valid(policy_)) {
        error_ = "unqualified_pairing";
        return {};
    }
    if (m.kind != Message::Kind::Rmc)
        return {};
    if (!m.time_valid || !m.utc_ns || *m.utc_ns % second) {
        previous_.reset();
        error_ = "invalid_utc";
        return {};
    }
    std::optional<Pulse> pulse;
    bool contained = false;
    for (const auto& captured : pulses_) {
        if (!captured.sequence)
            continue;
        const auto earliest = captured.raw_ns - captured.uncertainty_ns;
        const auto latest = captured.raw_ns + captured.uncertainty_ns;
        if (earliest > m.received_raw_ns)
            continue;
        const auto maximum_delay = m.received_raw_ns - earliest;
        if (maximum_delay < policy_.minimum_message_delay_ns ||
            (latest <= m.received_raw_ns &&
             m.received_raw_ns - latest > policy_.maximum_message_delay_ns))
            continue;
        if (pulse) {
            previous_.reset();
            error_ = "ambiguous_utc";
            return {};
        }
        pulse = captured;
        contained = latest <= m.received_raw_ns &&
                    m.received_raw_ns - latest >= policy_.minimum_message_delay_ns &&
                    maximum_delay <= policy_.maximum_message_delay_ns;
    }
    if (!pulse || !contained || *m.utc_ns % second || pulse->sequence <= consumed_sequence_ ||
        m.received_raw_ns < pulse->raw_ns ||
        m.received_raw_ns - pulse->raw_ns < policy_.minimum_message_delay_ns ||
        m.received_raw_ns - pulse->raw_ns > policy_.maximum_message_delay_ns) {
        error_ = "unpaired_utc";
        return {};
    }
    consumed_sequence_ = pulse->sequence;
    const auto offset = std::int64_t(policy_.utc_second_offset) * std::int64_t(second);
    if (policy_.edge_offset_ns > 0 && pulse->raw_ns < std::uint32_t(policy_.edge_offset_ns)) {
        error_ = "invalid_pps_offset";
        return {};
    }
    if ((policy_.edge_offset_ns < 0 &&
         pulse->raw_ns > UINT64_MAX - std::uint32_t(-policy_.edge_offset_ns)) ||
        (offset < 0 && *m.utc_ns < std::uint64_t(-offset)) ||
        (offset > 0 && *m.utc_ns > UINT64_MAX - std::uint64_t(offset))) {
        previous_.reset();
        error_ = "invalid_pps_offset";
        return {};
    }
    const auto adjusted_raw = policy_.edge_offset_ns >= 0
                                  ? pulse->raw_ns - std::uint32_t(policy_.edge_offset_ns)
                                  : pulse->raw_ns + std::uint32_t(-policy_.edge_offset_ns);
    if (adjusted_raw > m.received_raw_ns) {
        previous_.reset();
        error_ = "future_pps_epoch";
        return {};
    }
    const auto utc =
        offset >= 0 ? *m.utc_ns + std::uint64_t(offset) : *m.utc_ns - std::uint64_t(-offset);
    Observation value{adjusted_raw, utc, pulse->uncertainty_ns + policy_.receiver_uncertainty_ns,
                      pulse->sequence, pulse->raw_ns};
    const auto preceding = previous_;
    previous_ = value;
    if (!preceding || value.sequence != preceding->sequence + 1 ||
        value.utc_ns <= preceding->utc_ns || value.utc_ns - preceding->utc_ns != second) {
        error_ = "pairing_acquisition";
        return {};
    }
    error_ = {};
    return value;
}
std::optional<std::array<char, 7>> locator(const Position& p) {
    if (p.latitude_e7 < -900'000'000 || p.latitude_e7 > 900'000'000 ||
        p.longitude_e7 < -1'800'000'000 || p.longitude_e7 > 1'800'000'000)
        return {};
    const auto lon =
        std::min<std::int64_t>(std::int64_t(p.longitude_e7) + 1'800'000'000, 3'599'999'999LL);
    const auto lat =
        std::min<std::int64_t>(std::int64_t(p.latitude_e7) + 900'000'000, 1'799'999'999LL);
    return std::array<char, 7>{char('A' + lon / 200'000'000),
                               char('A' + lat / 100'000'000),
                               char('0' + lon / 20'000'000 % 10),
                               char('0' + lat / 10'000'000 % 10),
                               char('A' + lon % 20'000'000 * 24 / 20'000'000),
                               char('A' + lat % 10'000'000 * 24 / 10'000'000),
                               '\0'};
}
std::optional<std::uint64_t> utc_valid_until(std::uint64_t utc) {
    if (utc < 1'735'689'600ULL * second || utc >= 4'102'444'800ULL * second)
        return {};
    using namespace std::chrono;
    const year_month_day date{sys_days{days{utc / second / 86400}}};
    const auto month = date.year() / date.month();
    const auto start =
        std::uint64_t(sys_days{month / 1}.time_since_epoch().count()) * 86400ULL * second;
    const auto end = std::uint64_t(sys_days{(month + months{1}) / 1}.time_since_epoch().count()) *
                     86400ULL * second;
    if (utc < start + 5 * second || utc >= end - 5 * second)
        return {};
    return end - 5 * second;
}
} // namespace wsprrypico::time::gps
