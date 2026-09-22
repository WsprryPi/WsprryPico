#include "provisioning/activation.hpp"

namespace wsprrypico::provisioning {
ActivationCoordinator::~ActivationCoordinator() {
    if (state_ == ActivationState::PendingDelivery ||
        (state_ == ActivationState::Fault && !fail_closed_confirmed_))
        retry_fail_closed();
    clear_profile();
    request_id_.assign(request_id_.size(), '\0');
    request_id_.clear();
}

bool ActivationCoordinator::elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}

bool ActivationCoordinator::idle(const Activity& activity) {
    return !activity.owned && activity.output_known && !activity.output_active && !activity.armed &&
           !activity.running && !activity.failed;
}

void ActivationCoordinator::clear_profile() {
    if (has_profile_) {
        scrub(profile_);
        has_profile_ = false;
    }
}

bool ActivationCoordinator::stage(std::string_view request_id, const Profile& profile,
                                  std::uint64_t generation, std::uint64_t now_ms) {
    if (request_id.empty() || !generation || blocks_admission())
        return false;
    if (!platform_.close_admission(generation))
        return false;
    clear_profile();
    has_profile_ = true;
    profile_.device_id = profile.device_id;
    profile_.ssid = profile.ssid;
    profile_.password = profile.password;
    profile_.time_server = profile.time_server;
    profile_.hostname = profile.hostname;
    profile_.port = profile.port;
    profile_.server_certificate = profile.server_certificate;
    profile_.server_private_key = profile.server_private_key;
    profile_.client_ca = profile.client_ca;
    request_id_ = request_id;
    generation_ = generation;
    staged_ms_ = now_ms;
    state_ = ActivationState::PendingDelivery;
    fault_ = ActivationFault::None;
    fail_closed_confirmed_ = false;
    return true;
}

bool ActivationCoordinator::terminal_matches(std::string_view request_id,
                                             std::uint64_t generation) const {
    return generation && generation == generation_ && request_id == request_id_;
}

void ActivationCoordinator::retry_fail_closed() {
    if (!fail_closed_confirmed_)
        fail_closed_confirmed_ = platform_.fail_closed(generation_);
}

ActivationRelease ActivationCoordinator::latch(ActivationFault fault) {
    fault_ = fault;
    state_ = ActivationState::Fault;
    clear_profile();
    retry_fail_closed();
    return ActivationRelease::Fault;
}

ActivationRelease ActivationCoordinator::execute() {
    if (!has_profile_)
        return latch(ActivationFault::Stage);
    if (!platform_.prepare(profile_, generation_))
        return latch(ActivationFault::Prepare);
    if (!idle(platform_.activity()))
        return latch(ActivationFault::ActivityChanged);
    if (!platform_.quiesce())
        return latch(ActivationFault::Quiesce);
    if (!platform_.install(profile_, generation_))
        return latch(ActivationFault::Install);
    if (!platform_.restart())
        return latch(ActivationFault::Restart);
    clear_profile();
    state_ = ActivationState::Complete;
    fault_ = ActivationFault::None;
    fail_closed_confirmed_ = false;
    return ActivationRelease::Executed;
}

ActivationRelease ActivationCoordinator::release(std::string_view request_id,
                                                 std::uint64_t generation, std::uint64_t now_ms) {
    (void)now_ms;
    if (!terminal_matches(request_id, generation))
        return ActivationRelease::Stale;
    if (state_ == ActivationState::PendingDelivery)
        return execute();
    if (state_ == ActivationState::Fault && !fail_closed_confirmed_) {
        retry_fail_closed();
        return ActivationRelease::Fault;
    }
    return ActivationRelease::AlreadyTerminal;
}

void ActivationCoordinator::poll(std::uint64_t now_ms) {
    if (state_ == ActivationState::PendingDelivery &&
        elapsed(now_ms, staged_ms_, activation_delivery_timeout_ms))
        (void)execute();
    else if (state_ == ActivationState::Fault && !fail_closed_confirmed_)
        retry_fail_closed();
}

void ActivationCoordinator::committed_fault(std::string_view request_id, std::uint64_t generation,
                                            ActivationFault fault) {
    request_id_ = request_id;
    generation_ = generation;
    staged_ms_ = 0;
    (void)latch(fault == ActivationFault::None ? ActivationFault::Stage : fault);
}

ActivationStatus ActivationCoordinator::status() const {
    return {state_, fault_, generation_, fail_closed_confirmed_};
}
} // namespace wsprrypico::provisioning
