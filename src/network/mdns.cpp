#include "network/mdns.hpp"

#include "network/identity.hpp"

#include <limits>

namespace wsprrypico::network {
namespace {
void count(std::uint32_t& value) {
    if (value != std::numeric_limits<std::uint32_t>::max())
        ++value;
}
} // namespace
Mdns::Mdns(MdnsAdapter& adapter, std::string_view hostname) : adapter_(adapter) {
    if (hostname.empty())
        return;
    const auto canonical = canonical_local_hostname(hostname);
    if (!canonical) {
        permanent_failure_ = true;
        fail("invalid_hostname");
        return;
    }
    hostname_ = *canonical;
    label_ = hostname_.substr(0, hostname_.size() - 6);
    state_ = State::Waiting;
}
void Mdns::stop(bool goodbye) {
    if (registered_)
        adapter_.remove(goodbye);
    registered_ = false;
    address_ = 0;
}
void Mdns::fail(std::string_view reason) {
    stop(false);
    state_ = State::Failed;
    reason_ = reason;
    count(failures_);
}
void Mdns::poll(bool enabled, std::uint32_t address, std::uint64_t now_us) {
    // Never destroy lwIP data in its name callback: the responder still uses it.
    if (pending_conflict_) {
        stop(false);
        pending_conflict_ = false;
    }
    if (state_ == State::Unconfigured || state_ == State::Failed || state_ == State::Conflict)
        return;
    if (state_ == State::Withdrawing) {
        // An explicit finish/cancel owns teardown. Never re-advertise during drain.
        if (!enabled || !address || restart_)
            disable(false);
        return;
    }
    if (!enabled || !address) {
        stop(false);
        restart_ = false;
        state_ = State::Waiting;
        return;
    }
    if (registered_ && (address_ != address || restart_)) {
        if (address_ != address)
            count(address_changes_);
        stop(false);
        state_ = State::Waiting;
    }
    restart_ = false;
    if (!registered_) {
        if (!initialized_) {
            if (!adapter_.initialize()) {
                fail("initialization_failed");
                return;
            }
            initialized_ = true;
        }
        if (!adapter_.add(label_)) {
            fail("registration_failed");
            return;
        }
        registered_ = true;
        address_ = address;
        probe_started_us_ = now_us;
        state_ = State::Probing;
        count(registrations_);
    } else if (state_ == State::Probing && now_us - probe_started_us_ >= 30'000'000ULL) {
        fail("probe_timeout");
    }
}
void Mdns::name_result(bool success) {
    if (!registered_ || (state_ != State::Probing && state_ != State::Active))
        return;
    if (success)
        state_ = State::Active;
    else {
        state_ = State::Conflict;
        reason_ = "name_conflict";
        pending_conflict_ = true;
        count(conflicts_);
    }
}
bool Mdns::withdraw(bool link_usable) {
    if (state_ == State::Withdrawing)
        return true;
    if (!registered_ || state_ != State::Active || !link_usable)
        return false;
    state_ = State::Withdrawing;
    adapter_.withdraw();
    return true;
}
void Mdns::disable(bool link_usable) {
    stop(link_usable && state_ == State::Active);
    pending_conflict_ = false;
    if (state_ == State::Probing || state_ == State::Active || state_ == State::Withdrawing)
        state_ = State::Waiting;
}
void Mdns::retry() {
    if (permanent_failure_ || hostname_.empty())
        return;
    stop(false);
    pending_conflict_ = false;
    state_ = State::Waiting;
    reason_.clear();
}
void Mdns::identity_failure() {
    permanent_failure_ = true;
    fail("device_identity_mismatch");
}
std::string_view Mdns::state() const {
    switch (state_) {
    case State::Unconfigured:
        return "unconfigured";
    case State::Waiting:
        return "waiting_address";
    case State::Probing:
        return "probing";
    case State::Active:
        return "active";
    case State::Withdrawing:
        return "withdrawing";
    case State::Conflict:
        return "conflict";
    case State::Failed:
        return "failed";
    }
    return "failed";
}
std::string_view Mdns::advertised() const {
    return state_ == State::Active ? std::string_view(hostname_) : std::string_view{};
}
} // namespace wsprrypico::network
