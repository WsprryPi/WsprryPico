#include "provisioning/manager.hpp"

#include "network/identity.hpp"

#include <algorithm>
#include <array>
#include <charconv>

namespace wsprrypico::provisioning {
namespace {
std::span<const std::uint8_t> bytes(std::string_view text) {
    return {reinterpret_cast<const std::uint8_t*>(text.data()), text.size()};
}
wtp::PayloadDigest request_digest(std::string_view operation,
                                  std::initializer_list<std::string_view> fields,
                                  std::span<const std::uint8_t> payload = {}) {
    wtp::Sha256 hash;
    hash.update(bytes(operation));
    const std::uint8_t separator = 0;
    for (auto field : fields) {
        hash.update(std::span(&separator, 1));
        hash.update(bytes(field));
    }
    hash.update(std::span(&separator, 1));
    hash.update(payload);
    return hash.finish();
}
std::string number(std::uint64_t value) {
    std::array<char, 32> text{};
    const auto result = std::to_chars(text.data(), text.data() + text.size(), value);
    return {text.data(), result.ptr};
}
std::string_view transport_name(Transport transport) {
    return transport == Transport::Ble ? "ble" : "softap";
}
bool valid_principal(std::string_view principal) {
    return !principal.empty() && principal.size() <= 64 &&
           std::all_of(principal.begin(), principal.end(),
                       [](unsigned char c) { return c >= 33 && c < 127; });
}
bool busy(const Activity& activity) {
    return activity.owned || !activity.output_known || activity.output_active || activity.armed ||
           activity.running || activity.failed;
}
} // namespace

bool Manager::elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}
void Manager::expire(std::uint64_t now_ms) {
    replay_.erase(std::remove_if(replay_.begin(), replay_.end(),
                                 [now_ms](const auto& entry) {
                                     return elapsed(now_ms, entry.recorded_ms, replay_retention_ms);
                                 }),
                  replay_.end());
    if (session_ && elapsed(now_ms, session_->last_progress_ms, session_timeout_ms))
        terminate(State::Expired);
}
void Manager::poll(std::uint64_t now_ms) {
    expire(now_ms);
    if (activation_) {
        activation_->poll(now_ms);
        if (activation_->status().state == ActivationState::Fault)
            state_ = State::Failed;
    }
}
void Manager::terminate(State state) {
    if (session_) {
        volatile std::uint8_t* staged =
            session_->staged.empty() ? nullptr : session_->staged.data();
        for (std::size_t i = 0; i < session_->staged.size(); ++i)
            staged[i] = 0;
        std::vector<std::uint8_t>().swap(session_->staged);
        session_->principal.assign(session_->principal.size(), '\0');
        session_->principal.clear();
        session_->id.clear();
    }
    session_.reset();
    state_ = state;
}
std::optional<Result> Manager::replay(std::string_view request_id, const wtp::PayloadDigest& digest,
                                      std::uint64_t now_ms) {
    expire(now_ms);
    if (!network::valid_device_id(request_id))
        return Result{Code::InvalidRequest, store_.sequence()};
    const auto found =
        std::find_if(replay_.begin(), replay_.end(),
                     [request_id](const auto& entry) { return entry.request_id == request_id; });
    if (found == replay_.end())
        return {};
    if (found->digest != digest) {
        terminate(State::Failed);
        return Result{Code::Replay, store_.sequence()};
    }
    auto result = found->result;
    result.replayed = true;
    return result;
}
Result Manager::remember(std::string_view request_id, const wtp::PayloadDigest& digest,
                         Result result, std::uint64_t now_ms) {
    if (network::valid_device_id(request_id)) {
        if (replay_.size() == replay_capacity) {
            const auto eviction =
                std::find_if(replay_.begin(), replay_.end(), [this](const auto& entry) {
                    return !activation_ ||
                           !activation_->protects_replay(entry.request_id, entry.result.generation);
                });
            if (eviction == replay_.end())
                return result;
            replay_.erase(eviction);
        }
        replay_.push_back({std::string(request_id), digest, result, now_ms});
    }
    return result;
}

Result Manager::open(std::string_view request_id, std::string_view session_id,
                     std::string_view requested_device, Transport transport,
                     const Authorization& authorization, std::uint64_t now_ms) {
    const auto digest = request_digest(
        "open", {session_id, requested_device, transport == Transport::Ble ? "ble" : "softap",
                 authorization.principal, authorization.authenticated ? "1" : "0",
                 authorization.confidential ? "1" : "0", authorization.local ? "1" : "0"});
    if (auto prior = replay(request_id, digest, now_ms))
        return *prior;
    Result result{Code::Ok, store_.sequence()};
    if (!store_.healthy())
        result.code = Code::StorageFault;
    else if (!network::valid_device_id(session_id))
        result.code = Code::InvalidRequest;
    else if (!authorization.authenticated || !authorization.confidential || !authorization.local ||
             !valid_principal(authorization.principal))
        result.code = Code::AuthenticationRequired;
    else if (requested_device != device_id_ || !network::valid_device_id(requested_device))
        result.code = Code::WrongDevice;
    else if (activation_ && activation_->blocks_admission())
        result.code = activation_->status().state == ActivationState::Fault ? Code::ActivationFault
                                                                            : Code::SessionBusy;
    else if (session_)
        result.code = Code::SessionBusy;
    else {
        Session session;
        session.id = session_id;
        session.principal = authorization.principal;
        session.transport = transport;
        session.last_progress_ms = now_ms;
        session.staged.reserve(max_profile_bytes);
        session_ = std::move(session);
        state_ = State::Receiving;
        last_transport_ = transport;
    }
    return remember(request_id, digest, result, now_ms);
}

Result Manager::write(std::string_view request_id, std::string_view session_id, std::size_t offset,
                      std::span<const std::uint8_t> input, bool final, Transport transport,
                      const Authorization& authorization, std::uint64_t now_ms) {
    const auto digest =
        request_digest("write",
                       {session_id, number(offset), final ? "1" : "0", transport_name(transport),
                        authorization.principal, authorization.authenticated ? "1" : "0",
                        authorization.confidential ? "1" : "0", authorization.local ? "1" : "0"},
                       input);
    if (auto prior = replay(request_id, digest, now_ms))
        return *prior;
    Result result{Code::Ok, store_.sequence()};
    if (!authorization.authenticated || !authorization.confidential || !authorization.local ||
        !valid_principal(authorization.principal))
        result.code = Code::AuthenticationRequired;
    else if (!session_ || session_->id != session_id)
        result.code = Code::SessionNotFound;
    else if (session_->transport != transport || session_->principal != authorization.principal)
        result.code = Code::AuthenticationRequired;
    else if (session_->final || offset != session_->staged.size() || input.empty())
        result.code = Code::OutOfOrder;
    else if (session_->fragments == fragment_capacity ||
             input.size() > max_profile_bytes - session_->staged.size()) {
        result.code = Code::Oversize;
        terminate(State::Failed);
    } else {
        session_->staged.insert(session_->staged.end(), input.begin(), input.end());
        ++session_->fragments;
        session_->last_progress_ms = now_ms;
        session_->final = final;
        state_ = final ? State::Ready : State::Receiving;
        result.accepted_bytes = session_->staged.size();
    }
    return remember(request_id, digest, result, now_ms);
}

Result Manager::apply(std::string_view request_id, std::string_view session_id,
                      std::uint64_t expected_generation, const Activity& activity,
                      Transport transport, const Authorization& authorization,
                      std::uint64_t now_ms) {
    const auto digest = request_digest(
        "apply", {session_id, number(expected_generation), transport_name(transport),
                  authorization.principal, authorization.authenticated ? "1" : "0",
                  authorization.confidential ? "1" : "0", authorization.local ? "1" : "0"});
    if (auto prior = replay(request_id, digest, now_ms))
        return *prior;
    Result result{Code::Ok, store_.sequence()};
    if (!authorization.authenticated || !authorization.confidential || !authorization.local ||
        !valid_principal(authorization.principal))
        result.code = Code::AuthenticationRequired;
    else if (!session_ || session_->id != session_id)
        result.code = Code::SessionNotFound;
    else if (session_->transport != transport || session_->principal != authorization.principal)
        result.code = Code::AuthenticationRequired;
    else if (!session_->final)
        result.code = Code::Incomplete;
    else if (expected_generation != store_.sequence())
        result.code = Code::Conflict;
    else if (busy(activity))
        result.code = Code::Busy;
    else {
        const auto text = std::string_view(reinterpret_cast<const char*>(session_->staged.data()),
                                           session_->staged.size());
        auto profile = parse_profile(text);
        if (!profile) {
            result.code = Code::Malformed;
            terminate(State::Failed);
        } else if (profile->device_id != device_id_) {
            result.code = Code::WrongDevice;
            scrub(*profile);
            terminate(State::Failed);
        } else if (!validator_.validate(*profile)) {
            result.code = Code::CredentialInvalid;
            scrub(*profile);
            terminate(State::Failed);
        } else {
            auto canonical = serialize_profile(*profile);
            const auto previous_generation = store_.sequence();
            if (canonical.size() > max_profile_bytes || !store_.replace(canonical)) {
                result.code = Code::StorageFault;
                volatile char* raw = canonical.empty() ? nullptr : canonical.data();
                for (std::size_t i = 0; i < canonical.size(); ++i)
                    raw[i] = 0;
                scrub(*profile);
                terminate(State::Failed);
            } else {
                volatile char* raw = canonical.empty() ? nullptr : canonical.data();
                for (std::size_t i = 0; i < canonical.size(); ++i)
                    raw[i] = 0;
                result.generation = store_.sequence();
                if (activation_ && result.generation != previous_generation &&
                    !activation_->stage(request_id, *profile, result.generation, now_ms)) {
                    activation_->committed_fault(request_id, result.generation,
                                                 ActivationFault::Stage);
                    result.code = Code::ActivationFault;
                    scrub(*profile);
                    terminate(State::Failed);
                } else {
                    scrub(*profile);
                    terminate(State::Complete);
                }
            }
        }
    }
    return remember(request_id, digest, result, now_ms);
}

Result Manager::cancel(std::string_view request_id, std::string_view session_id,
                       Transport transport, const Authorization& authorization,
                       std::uint64_t now_ms) {
    const auto digest = request_digest(
        "cancel", {session_id, transport_name(transport), authorization.principal,
                   authorization.authenticated ? "1" : "0", authorization.confidential ? "1" : "0",
                   authorization.local ? "1" : "0"});
    if (auto prior = replay(request_id, digest, now_ms))
        return *prior;
    Result result{Code::Ok, store_.sequence()};
    if (!authorization.authenticated || !authorization.confidential || !authorization.local ||
        !valid_principal(authorization.principal))
        result.code = Code::AuthenticationRequired;
    else if (!session_ || session_->id != session_id)
        result.code = Code::SessionNotFound;
    else if (session_->transport != transport || session_->principal != authorization.principal)
        result.code = Code::AuthenticationRequired;
    else
        terminate(State::Cancelled);
    return remember(request_id, digest, result, now_ms);
}

ActivationRelease Manager::release_activation(std::string_view request_id, std::uint64_t generation,
                                              std::uint64_t now_ms) {
    if (!activation_)
        return ActivationRelease::Stale;
    const auto result = activation_->release(request_id, generation, now_ms);
    if (activation_->status().state == ActivationState::Fault)
        state_ = State::Failed;
    return result;
}

Status Manager::status() const {
    Status result;
    result.state = state_;
    result.transport = session_ ? session_->transport : last_transport_;
    result.generation = store_.sequence();
    result.staged_bytes = session_ ? session_->staged.size() : 0;
    result.fragments = session_ ? session_->fragments : 0;
    result.replay_entries = replay_.size();
    if (activation_)
        result.activation = activation_->status();
    return result;
}
} // namespace wsprrypico::provisioning
