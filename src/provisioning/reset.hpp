#pragma once

#include "provisioning/access.hpp"

#include <utility>

namespace wsprrypico::provisioning {
enum class ResetResult { Complete, Pending, Busy, Invalid, StorageFault, TargetFault };

class ResetTargets {
  public:
    virtual ~ResetTargets() = default;
    virtual Activity activity() const = 0;
    virtual bool erase_operational() = 0;
    virtual bool operational_erased() const = 0;
    virtual bool erase_bonds() = 0;
    virtual bool bonds_erased() const = 0;
};

class ResetCoordinator {
  public:
    ResetCoordinator(AccessStore& access, ProfileStore& profiles, ResetTargets& targets,
                     LocalIdentity identity)
        : access_(access), profiles_(profiles), targets_(targets), identity_(std::move(identity)) {}

    ResetResult begin(ResetLevel level, ProfileSource target_source,
                      const wtp::PayloadDigest& request_digest);
    ResetResult resume();
    bool pending() const {
        return access_.record() && access_.record()->reset.pending();
    }

  private:
    bool save(AccessRecord& record, ResetPhase phase);
    AccessStore& access_;
    ProfileStore& profiles_;
    ResetTargets& targets_;
    LocalIdentity identity_;
};
} // namespace wsprrypico::provisioning
