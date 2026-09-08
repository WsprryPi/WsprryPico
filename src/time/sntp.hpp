#pragma once
#include "time/utc_discipline.hpp"

#include <array>
#include <optional>
#include <span>

namespace wsprrypico::time {
inline constexpr std::uint64_t standalone_max_uncertainty_ns = 500'000'000ULL;
// Bounded unicast polling: retry lost exchanges twice, then back off. A
// correlated accepted observation restores the ordinary 64-second interval.
class SntpPollSchedule {
  public:
    bool due(std::uint64_t now_us) const {
        return !waiting_ || (now_us >= last_us_ && now_us - last_us_ >= delay_us_);
    }
    void sent(std::uint64_t now_us) {
        waiting_ = true;
        last_us_ = now_us;
        delay_us_ = ++attempt_ < 3 ? 2'000'000 : 64'000'000;
        if (attempt_ == 3)
            attempt_ = 0;
    }
    void accepted(std::uint64_t now_us) {
        waiting_ = true;
        last_us_ = now_us;
        delay_us_ = 64'000'000;
        attempt_ = 0;
    }
    void reset() {
        waiting_ = false;
        attempt_ = 0;
    }

  private:
    std::uint64_t last_us_ = 0, delay_us_ = 0;
    unsigned attempt_ = 0;
    bool waiting_ = false;
};
// Minimal unicast SNTP exchange. The transport must verify peer IPv4 and UDP 123.
class Sntp {
  public:
    explicit Sntp(UtcDiscipline& clock) : clock_(clock) {}
    std::array<std::uint8_t, 48> request(std::uint64_t monotonic_ns, std::uint64_t nonce);
    bool receive(std::span<const std::uint8_t> packet, std::uint64_t monotonic_ns);
    void cancel() {
        pending_ = false;
    }
    std::uint64_t last_rtt_ns() const {
        return last_rtt_ns_;
    }
    std::optional<std::uint64_t> last_uncertainty_ns() const {
        return last_uncertainty_ns_;
    }
    bool denied() const {
        return denied_;
    }

  private:
    UtcDiscipline& clock_;
    std::uint64_t sent_ = 0, nonce_ = 0;
    bool pending_ = false, denied_ = false;
    std::uint64_t last_rtt_ns_ = 0;
    std::optional<std::uint64_t> last_uncertainty_ns_;
};
inline constexpr std::uint64_t sntp_min_utc_ns = 1'735'689'600'000'000'000ULL; // 2025-01-01
inline constexpr std::uint64_t sntp_max_utc_ns = 4'102'444'800'000'000'000ULL; // 2100-01-01
} // namespace wsprrypico::time
