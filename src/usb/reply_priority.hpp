#pragma once

#include <cstdint>

namespace wsprrypico::usb {
// Let a multi-packet Console reply drain before the next expensive TLS step.
// An unread or continuously refilled Console gets at most 100 ms per second;
// it cannot renew the grace period by alternating empty and pending states.
class ReplyPriority {
  public:
    bool defer_handshake(std::uint64_t now_us, bool pending) {
        if (!pending)
            return false;
        if (!started_ || now_us - started_us_ >= kPeriodUs) {
            started_ = true;
            started_us_ = now_us;
        }
        return now_us - started_us_ < kGraceUs;
    }

  private:
    static constexpr std::uint64_t kGraceUs = 100'000;
    static constexpr std::uint64_t kPeriodUs = 1'000'000;
    std::uint64_t started_us_ = 0;
    bool started_ = false;
};
} // namespace wsprrypico::usb
