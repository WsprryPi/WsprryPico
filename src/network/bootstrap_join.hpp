#pragma once

#include "provisioning/network_profile.hpp"

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
// A journal attempt is consumed once. An unresolved durable result cannot
// turn into rollback through expiration, cancellation, an ACK or a repeated poll.
class BootstrapCommitGate {
  public:
    bool begin();
    provisioning::SetupCommitResult commit(provisioning::ProfileStore& store,
                                           provisioning::ProfileSource source,
                                           std::string_view payload, std::uint64_t now_ms);
    bool reconcile() const {
        return settled_ && result_ == provisioning::SetupCommitResult::Reconcile;
    }
    bool cancellation_allowed() const {
        return !reconcile();
    }
    bool trial_allowed() const {
        return !settled_;
    }
    bool result_verified() const {
        return !reconcile();
    }
    bool restart_due(std::uint64_t now_ms) const;

  private:
    bool settled_ = false;
    provisioning::SetupCommitResult result_ = provisioning::SetupCommitResult::Reconcile;
    std::uint64_t settled_ms_ = 0;
};
} // namespace wsprrypico::network
