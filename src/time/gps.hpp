// SPDX-License-Identifier: MIT
#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::time::gps {
inline constexpr std::uint64_t second = 1'000'000'000ULL;
struct Position {
    std::int32_t latitude_e7 = 0, longitude_e7 = 0;
    std::uint64_t observed_raw_ns = 0;
    bool operator==(const Position&) const = default;
};
struct Message {
    enum class Kind { Rmc, Gga } kind = Kind::Rmc;
    std::uint64_t received_raw_ns = 0;
    std::optional<std::uint64_t> utc_ns;
    std::optional<Position> position;
    unsigned satellites = 0;
    bool time_valid = false, position_valid = false;
};
// A bounded, allocation-free receive parser. The timestamp is the arrival of
// the first '$', not the time the application eventually drains the sentence.
class Parser {
  public:
    std::optional<Message> byte(char value, std::uint64_t raw_ns);
    void lost();
    std::uint32_t rejected() const {
        return rejected_;
    }
    std::uint32_t accepted() const {
        return accepted_;
    }

  private:
    std::array<char, 160> buffer_{};
    unsigned size_ = 0;
    std::uint64_t started_ns_ = 0;
    std::uint32_t rejected_ = 0, accepted_ = 0;
    bool carriage_return_ = false;
};
struct Pulse {
    std::uint64_t raw_ns = 0, uncertainty_ns = 0, sequence = 0;
};
struct Observation {
    std::uint64_t raw_ns = 0, utc_ns = 0, uncertainty_ns = 0, sequence = 0;
    std::uint64_t capture_raw_ns = 0;
};
struct PairingPolicy {
    // Receiver-specific statement: RMC describes the preceding rising edge
    // plus this integer offset. A policy is usable only after qualification.
    bool qualified = false;
    int utc_second_offset = 0;
    std::uint64_t minimum_message_delay_ns = 0;
    std::uint64_t maximum_message_delay_ns = 800'000'000;
    std::uint64_t receiver_uncertainty_ns = 100'000;
    std::int32_t edge_offset_ns = 0; // Positive: captured edge follows the UTC boundary.
};
bool valid(const PairingPolicy&);
class Pairer {
  public:
    explicit Pairer(PairingPolicy policy) : policy_(policy) {}
    bool pulse(Pulse pulse);
    std::optional<Pulse> preceding_pulse(std::uint64_t sentence_started_raw_ns) const;
    std::optional<Observation> message(const Message& message);
    void lost();
    std::string_view error() const {
        return error_;
    }

  private:
    PairingPolicy policy_;
    std::optional<Pulse> latest_, preceding_;
    std::optional<Observation> previous_;
    std::uint64_t consumed_sequence_ = 0, last_pulse_sequence_ = 0, last_pulse_raw_ns_ = 0;
    std::string_view error_ = "awaiting_pps";
};
// Six-character Maidenhead; +90/+180 belong to the final representable cell.
std::optional<std::array<char, 7>> locator(const Position&);
// RMC contains UTC, but no advance leap announcement. This receive-only
// profile cannot authorize an interval crossing a potential month-end leap.
// Reacquire beyond a five-second guard on either side; never guess a leap sign.
std::optional<std::uint64_t> utc_valid_until(std::uint64_t utc_ns);
} // namespace wsprrypico::time::gps
