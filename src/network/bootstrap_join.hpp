#pragma once

#include <cstdint>

namespace wsprrypico::network {
enum class BootstrapJoinResult { Waiting, Ready, TimedOut };

// Monotonic gate for an AP-preserving station trial. The caller owns the
// radio and journal. Only Ready may lead to a commit.
class BootstrapJoinGate {
  public:
    void begin(std::uint64_t now_ms);
    BootstrapJoinResult trial(std::uint64_t now_ms, bool link, bool address) const;
    void finish();

  private:
    std::uint64_t started_ms_ = 0;
    bool started_ = false;
};
} // namespace wsprrypico::network
