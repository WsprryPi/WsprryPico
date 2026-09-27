#pragma once

#include <cstdint>

namespace wsprrypico::network {
enum class BootstrapJoinResult { Waiting, Ready, TimedOut };

// Monotonic gate for an AP-preserving station trial and postcommit AP withdrawal.
// The caller owns the radio and journal. Only Ready may lead to a commit.
class BootstrapJoinGate {
  public:
    void begin(std::uint64_t now_ms);
    BootstrapJoinResult trial(std::uint64_t now_ms, bool link, bool address) const;
    void finish(bool committed);
    void service(std::uint64_t now_ms, bool link, bool address);
    bool withdraw(std::uint64_t now_ms, bool acknowledged, bool reply_active) const;
    bool committed() const {
        return committed_;
    }

  private:
    std::uint64_t started_ms_ = 0, stable_since_ms_ = 0;
    bool started_ = false, committed_ = false, stable_ = false;
};
} // namespace wsprrypico::network
