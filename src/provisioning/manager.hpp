#pragma once

#include "provisioning/activation.hpp"
#include "provisioning/storage.hpp"
#include "wtp/sha256.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace wsprrypico::provisioning {
inline constexpr std::uint64_t session_timeout_ms = 30'000;
inline constexpr std::uint64_t replay_retention_ms = 300'000;
inline constexpr std::size_t replay_capacity = 8;
// Every accepted fragment is nonempty, so the byte ceiling also bounds the
// worst-case one-byte fragmentation without imposing a smaller transfer limit.
inline constexpr std::size_t fragment_capacity = max_profile_bytes;

enum class Transport { Ble, SoftAp };
enum class State { Idle, Receiving, Ready, Complete, Cancelled, Expired, Failed };
enum class Code {
    Ok,
    InvalidRequest,
    AuthenticationRequired,
    WrongDevice,
    SessionBusy,
    SessionNotFound,
    OutOfOrder,
    Incomplete,
    Oversize,
    Malformed,
    CredentialInvalid,
    Conflict,
    Busy,
    Replay,
    Timeout,
    Uncertainty,
    StorageFault,
    ActivationFault
};

struct Result {
    Code code = Code::Ok;
    std::uint64_t generation = 0;
    std::size_t accepted_bytes = 0;
    bool replayed = false;
    bool ok() const {
        return code == Code::Ok;
    }
};
struct Authorization {
    bool authenticated = false;
    bool confidential = false;
    bool local = false;
    std::string principal;
};
struct Status {
    State state = State::Idle;
    Transport transport = Transport::Ble;
    std::uint64_t generation = 0;
    std::size_t staged_bytes = 0;
    std::size_t fragments = 0;
    std::size_t replay_entries = 0;
    ActivationStatus activation;
};

class Manager {
  public:
    Manager(ProfileStore& store, CredentialValidator& validator, std::string device_id,
            ActivationCoordinator* activation = nullptr)
        : store_(store), validator_(validator), device_id_(std::move(device_id)),
          activation_(activation) {}
    ~Manager() {
        terminate(State::Cancelled);
    }
    Manager(const Manager&) = delete;
    Manager& operator=(const Manager&) = delete;
    Result open(std::string_view request_id, std::string_view session_id,
                std::string_view requested_device, Transport transport,
                const Authorization& authorization, std::uint64_t now_ms);
    Result write(std::string_view request_id, std::string_view session_id, std::size_t offset,
                 std::span<const std::uint8_t> bytes, bool final, Transport transport,
                 const Authorization& authorization, std::uint64_t now_ms);
    Result apply(std::string_view request_id, std::string_view session_id,
                 std::uint64_t expected_generation, const Activity& activity, Transport transport,
                 const Authorization& authorization, std::uint64_t now_ms);
    Result cancel(std::string_view request_id, std::string_view session_id, Transport transport,
                  const Authorization& authorization, std::uint64_t now_ms);
    ActivationRelease release_activation(std::string_view request_id, std::uint64_t generation,
                                         std::uint64_t now_ms);
    std::optional<wtp::PayloadDigest> staged_digest(std::string_view session_id,
                                                    Transport transport,
                                                    const Authorization& authorization,
                                                    std::uint64_t expected_generation) const;
    void poll(std::uint64_t now_ms);
    Status status() const;

  private:
    struct Session {
        std::string id;
        std::string principal;
        Transport transport = Transport::Ble;
        std::uint64_t last_progress_ms = 0;
        std::vector<std::uint8_t> staged;
        std::size_t fragments = 0;
        bool final = false;
    };
    struct ReplayEntry {
        std::string request_id;
        wtp::PayloadDigest digest{};
        Result result;
        std::uint64_t recorded_ms = 0;
    };
    std::optional<Result> replay(std::string_view request_id, const wtp::PayloadDigest& digest,
                                 std::uint64_t now_ms);
    Result remember(std::string_view request_id, const wtp::PayloadDigest& digest, Result result,
                    std::uint64_t now_ms);
    void terminate(State state);
    void expire(std::uint64_t now_ms);
    static bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit);

    ProfileStore& store_;
    CredentialValidator& validator_;
    std::string device_id_;
    ActivationCoordinator* activation_ = nullptr;
    std::optional<Session> session_;
    std::vector<ReplayEntry> replay_;
    State state_ = State::Idle;
    Transport last_transport_ = Transport::Ble;
};
} // namespace wsprrypico::provisioning
