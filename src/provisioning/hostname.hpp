#pragma once

#include "provisioning/consumer_claim_commit.hpp"

namespace wsprrypico::provisioning {
// The profile owns the saved name. Active names and credentials are boot snapshots.
class HostnameSettings {
  public:
    HostnameSettings(ProfileStore& store, RuntimeProfile& runtime,
                     ConsumerClaimCommitPlatform& platform, std::string device, std::string active,
                     std::string default_name)
        : store_(store), runtime_(runtime), platform_(platform), device_(std::move(device)),
          active_(std::move(active)), default_(std::move(default_name)) {}
    std::string readback(std::string_view boot) const;
    std::string revision_context() const;
    // Empty means committed/no-op; errors never contain credentials.
    std::string save(const std::optional<std::string>& hostname);

  private:
    ProfileStore& store_;
    RuntimeProfile& runtime_;
    ConsumerClaimCommitPlatform& platform_;
    std::string device_, active_, default_;
};
} // namespace wsprrypico::provisioning
