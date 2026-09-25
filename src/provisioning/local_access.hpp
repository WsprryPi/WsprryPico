#pragma once

#include "provisioning/access.hpp"
#include "provisioning/manager.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::provisioning {
inline constexpr std::uint64_t enrollment_window_ms = 120'000;
inline constexpr std::uint64_t proof_lifetime_ms = 120'000;
inline constexpr std::uint64_t softap_inactivity_ms = 15 * 60'000;
inline constexpr std::uint64_t softap_absolute_ms = 12 * 60 * 60'000;
inline constexpr std::size_t softap_session_capacity = 4;

enum class AccessCode {
    Ok,
    Invalid,
    AuthenticationRequired,
    ConfirmationRequired,
    WrongDevice,
    Busy,
    Capacity,
    Expired,
    Conflict,
    StorageFault,
    BondEraseFault,
};

struct RequestBinding {
    std::string device_id;
    std::string principal;
    std::string session_id;
    std::string operation;
    std::string nonce;
    std::uint64_t current_generation = 0;
    std::uint64_t target_generation = 0;
    wtp::PayloadDigest parameters{};
    bool operator==(const RequestBinding&) const = default;
};

class RandomSource {
  public:
    virtual ~RandomSource() = default;
    virtual bool fill(std::span<std::uint8_t> bytes) = 0;
};

class BondStore {
  public:
    virtual ~BondStore() = default;
    virtual bool erase(std::uint64_t peer) = 0;
    virtual bool erase_all() = 0;
};

enum class SoftApOperation {
    Hello,
    Status,
    Abort,
    Time,
    Load,
    Arm,
    Configure,
    Provision,
    AccessAdmin,
};

struct SoftApLogin {
    AccessCode code = AccessCode::Invalid;
    std::string token;
    std::string principal;
    SoftApLogin() = default;
    SoftApLogin(AccessCode value, std::string issued = {}, std::string identity = {})
        : code(value), token(std::move(issued)), principal(std::move(identity)) {}
};

struct SoftApAuthority {
    AccessCode code = AccessCode::Invalid;
    std::string principal;
    bool owner_only_grace = false;
    std::string wtp_session;
    SoftApAuthority() = default;
    SoftApAuthority(AccessCode value, std::string identity = {}, bool grace = false,
                    std::string mapped_session = {})
        : code(value), principal(std::move(identity)), owner_only_grace(grace),
          wtp_session(std::move(mapped_session)) {}
};

struct BleAdmission {
    AccessCode code = AccessCode::Invalid;
    std::string principal;
    bool provisional = false;
    BleAdmission() = default;
    BleAdmission(AccessCode value, std::string identity = {}, bool pending = false)
        : code(value), principal(std::move(identity)), provisional(pending) {}
};

class LocalAccessController {
  public:
    LocalAccessController(AccessStore& store, BondStore& bonds, RandomSource& random,
                          std::string device_id, std::string boot_id, LocalIdentity identity);
    ~LocalAccessController();
    LocalAccessController(const LocalAccessController&) = delete;
    LocalAccessController& operator=(const LocalAccessController&) = delete;

    AccessCode prove_password(std::string_view password, const RequestBinding& binding,
                              std::uint64_t now_ms);
    AccessCode confirm_local(const RequestBinding& binding, std::uint64_t now_ms);
    void invalidate_binding(std::string_view principal, std::string_view session_id);
    AccessCode initialize_default(const RequestBinding& binding, const Activity& activity,
                                  std::uint64_t now_ms);
    AccessCode open_enrollment(const RequestBinding& binding, const Activity& activity,
                               std::uint64_t now_ms);
    bool enrollment_open(std::uint64_t now_ms) const;

    BleAdmission ble_connect(std::uint64_t peer, bool encrypted, bool new_pairing,
                             std::string session_id, std::uint64_t now_ms);
    BleAdmission ble_authorize(std::string_view password, std::uint64_t now_ms);
    bool expire_provisional_bond(std::uint64_t now_ms);
    bool ble_disconnect();
    AccessCode remove_bond(std::uint64_t peer, const RequestBinding& binding,
                           const Activity& activity, std::uint64_t now_ms);

    SoftApLogin softap_login(std::string_view password, std::uint64_t now_ms,
                             std::string_view protected_wtp_session = {});
    AccessCode bind_softap_session(std::string_view token, std::string_view wtp_session,
                                   std::uint64_t now_ms);
    SoftApAuthority softap_authorize(std::string_view token, SoftApOperation operation,
                                     std::string_view wtp_session,
                                     std::string_view active_owner_session,
                                     const Activity& activity, std::uint64_t now_ms);
    AccessCode softap_logout(std::string_view token, std::string_view wtp_session,
                             std::string_view active_owner_session, const Activity& activity,
                             std::uint64_t now_ms);
    std::size_t live_softap_sessions(std::uint64_t now_ms,
                                     std::string_view protected_wtp_session = {});

    AccessCode change_password(std::string_view replacement, const RequestBinding& binding,
                               const Activity& activity, std::uint64_t now_ms);
    AccessCode set_field_mode(bool enabled, const RequestBinding& binding, const Activity& activity,
                              std::uint64_t now_ms);
    AccessCode sensitive_ready(const RequestBinding& binding, const Activity& activity,
                               std::uint64_t now_ms) const;
    AccessCode authorize_sensitive(const RequestBinding& binding, const Activity& activity,
                                   std::uint64_t now_ms);
    void invalidate_all_volatile();

    static std::string cookie_header(std::string_view token);
    bool ble_available() const {
        return store_.healthy() && store_.record() && !store_.record()->ble_disabled;
    }
    Authorization ble_authorization() const;
    const LocalIdentity& identity() const {
        return identity_;
    }
    bool default_password_active() const {
        return store_.record() && store_.record()->default_password;
    }

  private:
    struct Proof {
        RequestBinding binding;
        std::uint64_t issued_ms = 0;
        std::uint64_t epoch = 0;
        bool password = false;
        bool confirmation = false;
        bool active = false;
    };
    struct BleConnection {
        std::uint64_t peer = 0;
        std::string session_id;
        bool encrypted = false;
        bool provisional = false;
        bool authorized = false;
    };
    struct SoftApSession {
        std::string token;
        std::string principal;
        std::string boot_id;
        std::string wtp_session;
        std::uint64_t epoch = 0;
        std::uint64_t created_ms = 0;
        std::uint64_t last_activity_ms = 0;
        bool live = false;
    };

    bool valid_binding(const RequestBinding& binding) const;
    AccessCode consume(const RequestBinding& binding, bool need_password, bool need_confirmation,
                       std::uint64_t now_ms);
    AccessCode consume_either(const RequestBinding& binding, std::uint64_t now_ms);
    bool password_matches(std::string_view candidate) const;
    bool retained_bond(std::uint64_t peer) const;
    std::string bond_principal(std::uint64_t peer) const;
    void clear_ble();
    void clear_session(SoftApSession& session);
    void reclaim(std::uint64_t now_ms, std::string_view protected_wtp_session);
    SoftApSession* find_session(std::string_view token);
    bool mark_ble_disabled();

    AccessStore& store_;
    BondStore& bonds_;
    RandomSource& random_;
    std::string device_id_;
    std::string boot_id_;
    LocalIdentity identity_;
    Proof proof_;
    BleConnection ble_;
    std::array<SoftApSession, softap_session_capacity> softap_{};
    std::uint64_t enrollment_started_ms_ = 0;
    bool enrollment_active_ = false;
};
} // namespace wsprrypico::provisioning
