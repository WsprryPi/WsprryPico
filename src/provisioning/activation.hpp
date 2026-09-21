#pragma once

#include "provisioning/profile.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
inline constexpr std::uint64_t activation_delivery_timeout_ms = 5'000;

struct Activity {
    bool owned = false;
    bool output_known = true;
    bool output_active = false;
    bool armed = false;
    bool running = false;
    bool failed = false;
};

enum class ActivationState { Idle, PendingDelivery, Complete, Fault };
enum class ActivationFault { None, Stage, Prepare, ActivityChanged, Quiesce, Install, Restart };
enum class ActivationRelease { Executed, Fault, AlreadyTerminal, Stale };

struct ActivationStatus {
    ActivationState state = ActivationState::Idle;
    ActivationFault fault = ActivationFault::None;
    std::uint64_t generation = 0;
    bool fail_closed_confirmed = false;
};

// Core-0 platform boundary. prepare() may reserve resources but must not make
// the old runtime unavailable. activity() is sampled after prepare() and
// immediately before quiesce(). Implementations must not abort, release or clear
// job/RF ownership or infer inactive output; quiesce() and fail_closed() are
// network-runtime-only operations. None of these methods may retain Profile views.
class ActivationPlatform {
  public:
    virtual ~ActivationPlatform() = default;
    virtual bool prepare(const Profile& profile, std::uint64_t generation) = 0;
    virtual Activity activity() const = 0;
    virtual bool quiesce() = 0;
    virtual bool install(const Profile& profile, std::uint64_t generation) = 0;
    virtual bool restart() = 0;
    // Must be idempotent: release(), poll() and destruction may retry until the
    // platform confirms that superseded runtime trust is no longer active.
    virtual bool fail_closed(std::uint64_t generation) = 0;
};

// Owns one committed profile while its nonsensitive apply response is awaiting
// a terminal transport callback. A timeout releases the action so lost replies
// cannot leave superseded trust active indefinitely. The referenced platform
// must outlive the coordinator; destruction attempts fail-closed before secrets
// are scrubbed when committed activation has not reached a safe terminal state.
class ActivationCoordinator {
  public:
    explicit ActivationCoordinator(ActivationPlatform& platform) : platform_(platform) {}
    ~ActivationCoordinator();
    ActivationCoordinator(const ActivationCoordinator&) = delete;
    ActivationCoordinator& operator=(const ActivationCoordinator&) = delete;

    bool stage(std::string_view request_id, const Profile& profile, std::uint64_t generation,
               std::uint64_t now_ms);
    ActivationRelease release(std::string_view request_id, std::uint64_t generation,
                              std::uint64_t now_ms);
    void poll(std::uint64_t now_ms);
    void committed_fault(std::string_view request_id, std::uint64_t generation,
                         ActivationFault fault);
    bool blocks_admission() const {
        return state_ == ActivationState::PendingDelivery || state_ == ActivationState::Fault;
    }
    bool protects_replay(std::string_view request_id, std::uint64_t generation) const {
        return blocks_admission() && terminal_matches(request_id, generation);
    }
    ActivationStatus status() const;

  private:
    static bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit);
    static bool idle(const Activity& activity);
    ActivationRelease execute();
    ActivationRelease latch(ActivationFault fault);
    void retry_fail_closed();
    void clear_profile();
    bool terminal_matches(std::string_view request_id, std::uint64_t generation) const;

    ActivationPlatform& platform_;
    Profile profile_;
    bool has_profile_ = false;
    std::string request_id_;
    std::uint64_t generation_ = 0;
    std::uint64_t staged_ms_ = 0;
    ActivationState state_ = ActivationState::Idle;
    ActivationFault fault_ = ActivationFault::None;
    bool fail_closed_confirmed_ = false;
};
} // namespace wsprrypico::provisioning
