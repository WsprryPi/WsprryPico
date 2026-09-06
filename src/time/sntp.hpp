#pragma once
#include "time/utc_discipline.hpp"

#include <array>
#include <span>

namespace wsprrypico::time {
// Minimal unicast SNTP exchange. The transport must verify peer IPv4 and UDP 123.
class Sntp {
  public:
    explicit Sntp(UtcDiscipline& clock) : clock_(clock) {}
    std::array<std::uint8_t, 48> request(std::uint64_t monotonic_ns, std::uint64_t nonce);
    bool receive(std::span<const std::uint8_t> packet, std::uint64_t monotonic_ns);
    void cancel() {
        pending_ = false;
    }
    bool denied() const {
        return denied_;
    }

  private:
    UtcDiscipline& clock_;
    std::uint64_t sent_ = 0, nonce_ = 0;
    bool pending_ = false, denied_ = false;
};
inline constexpr std::uint64_t sntp_min_utc_ns = 1'735'689'600'000'000'000ULL; // 2025-01-01
inline constexpr std::uint64_t sntp_max_utc_ns = 4'102'444'800'000'000'000ULL; // 2100-01-01
} // namespace wsprrypico::time
