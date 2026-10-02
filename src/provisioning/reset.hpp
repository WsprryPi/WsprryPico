#pragma once

#include "provisioning/access.hpp"

#include <utility>

namespace wsprrypico::provisioning {
// Checkpoints occur only after the corresponding durable transition succeeds.
// An optional observer is used by the separately compiled inhibited fault fixture.
enum class ResetCheckpoint : std::uint8_t {
    Intent = 1,
    PreservationComplete,
    SourceSelected,
    AccessReset,
    OperationalErased,
    BondsCleared,
    Complete
};
enum class ResetResult { Complete, Pending, Busy, Invalid, StorageFault, TargetFault };

class ResetTargets {
  public:
    virtual ~ResetTargets() = default;
    virtual Activity activity() const = 0;
    virtual bool preserve_operational(const ProfileStore&) {
        return true;
    }
    virtual bool clear_profile(ProfileStore& profiles, ProfileSource target) {
        return profiles.select(target);
    }
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

    using CheckpointObserver = void (*)(ResetCheckpoint);
    void checkpoint_observer(CheckpointObserver observer) {
        observer_ = observer;
    }
    ResetResult begin(ResetLevel level, ProfileSource target_source,
                      const wtp::PayloadDigest& request_digest);
    ResetResult resume();
    bool blocks_admission() const {
        return uncertain_intent_ || pending();
    }
    bool pending() const {
        return access_.record() && access_.record()->reset.pending();
    }

  private:
    bool save(AccessRecord& record, ResetPhase phase);
    void checkpoint(ResetCheckpoint stage) {
        if (observer_)
            observer_(stage);
    }
    CheckpointObserver observer_ = nullptr;
    bool uncertain_intent_ = false;
    AccessStore& access_;
    ProfileStore& profiles_;
    ResetTargets& targets_;
    LocalIdentity identity_;
};
} // namespace wsprrypico::provisioning
