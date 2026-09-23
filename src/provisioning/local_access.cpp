#include "provisioning/local_access.hpp"

#include "wtp/sha256.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <limits>
#include <utility>

namespace wsprrypico::provisioning {
namespace {
bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}

void secure_clear(std::string& value) {
    volatile char* data = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        data[i] = 0;
    std::string{}.swap(value);
}

bool constant_equal(std::string_view left, std::string_view right) {
    std::size_t difference = left.size() ^ right.size();
    const auto maximum = std::max(left.size(), right.size());
    for (std::size_t i = 0; i < maximum; ++i) {
        const auto a = i < left.size() ? static_cast<unsigned char>(left[i]) : 0;
        const auto b = i < right.size() ? static_cast<unsigned char>(right[i]) : 0;
        difference |= a ^ b;
    }
    return difference == 0;
}

std::string hex(std::span<const std::uint8_t> bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(bytes.size() * 2);
    for (auto byte : bytes) {
        result.push_back(digits[byte >> 4]);
        result.push_back(digits[byte & 15]);
    }
    return result;
}

bool zero_digest(const wtp::PayloadDigest& digest) {
    return std::all_of(digest.begin(), digest.end(), [](std::uint8_t value) { return value == 0; });
}

bool bounded_text(std::string_view value, std::size_t maximum) {
    return !value.empty() && value.size() <= maximum &&
           std::all_of(value.begin(), value.end(),
                       [](unsigned char byte) { return byte >= 33 && byte < 127; });
}

bool grace_operation(SoftApOperation operation) {
    return operation == SoftApOperation::Status || operation == SoftApOperation::Abort ||
           operation == SoftApOperation::Time;
}
} // namespace

LocalAccessController::LocalAccessController(AccessStore& store, BondStore& bonds,
                                             RandomSource& random, std::string device_id,
                                             std::string boot_id, LocalIdentity identity)
    : store_(store), bonds_(bonds), random_(random), device_id_(std::move(device_id)),
      boot_id_(std::move(boot_id)), identity_(std::move(identity)) {}

LocalAccessController::~LocalAccessController() {
    invalidate_all_volatile();
}

bool LocalAccessController::valid_binding(const RequestBinding& binding) const {
    return binding.device_id == device_id_ &&
           bounded_text(binding.principal, 64) &&
           bounded_text(binding.session_id, 64) &&
           bounded_text(binding.operation, 32) &&
           bounded_text(binding.nonce, 64) &&
           !zero_digest(binding.parameters);
}

bool LocalAccessController::password_matches(std::string_view candidate) const {
    return store_.record() && constant_equal(candidate, store_.record()->password);
}

AccessCode LocalAccessController::prove_password(std::string_view password,
                                                 const RequestBinding& binding,
                                                 std::uint64_t now_ms) {
    if (!store_.healthy())
        return AccessCode::StorageFault;
    if (!valid_binding(binding))
        return binding.device_id == device_id_ ? AccessCode::Invalid : AccessCode::WrongDevice;
    if (!password_matches(password))
        return AccessCode::AuthenticationRequired;
    proof_.binding = binding;
    proof_.issued_ms = now_ms;
    proof_.epoch = store_.record()->epoch;
    proof_.password = true;
    proof_.confirmation = false;
    proof_.active = true;
    return AccessCode::Ok;
}

AccessCode LocalAccessController::confirm_local(const RequestBinding& binding,
                                                std::uint64_t now_ms) {
    if (!valid_binding(binding))
        return binding.device_id == device_id_ ? AccessCode::Invalid : AccessCode::WrongDevice;
    if (proof_.active && proof_.binding == binding &&
        !elapsed(now_ms, proof_.issued_ms, proof_lifetime_ms)) {
        proof_.confirmation = true;
        return AccessCode::Ok;
    }
    proof_.binding = binding;
    proof_.issued_ms = now_ms;
    proof_.epoch = store_.record() ? store_.record()->epoch : 0;
    proof_.password = false;
    proof_.confirmation = true;
    proof_.active = true;
    return AccessCode::Ok;
}

AccessCode LocalAccessController::consume(const RequestBinding& binding, bool need_password,
                                          bool need_confirmation, std::uint64_t now_ms) {
    const bool valid = proof_.active && proof_.binding == binding &&
                       !elapsed(now_ms, proof_.issued_ms, proof_lifetime_ms) &&
                       (!store_.record() || proof_.epoch == store_.record()->epoch);
    AccessCode result = AccessCode::Ok;
    if (!valid)
        result = need_password ? AccessCode::AuthenticationRequired : AccessCode::ConfirmationRequired;
    else if (need_password && !proof_.password)
        result = AccessCode::AuthenticationRequired;
    else if (need_confirmation && !proof_.confirmation)
        result = AccessCode::ConfirmationRequired;
    proof_ = {};
    return result;
}

AccessCode LocalAccessController::consume_either(const RequestBinding& binding,
                                                 std::uint64_t now_ms) {
    const bool valid = proof_.active && proof_.binding == binding &&
                       !elapsed(now_ms, proof_.issued_ms, proof_lifetime_ms) &&
                       (!store_.record() || proof_.epoch == store_.record()->epoch) &&
                       (proof_.password || proof_.confirmation);
    proof_ = {};
    return valid ? AccessCode::Ok : AccessCode::AuthenticationRequired;
}

void LocalAccessController::invalidate_binding(std::string_view principal,
                                               std::string_view session_id) {
    if (proof_.active && proof_.binding.principal == principal &&
        proof_.binding.session_id == session_id)
        proof_ = {};
}

AccessCode LocalAccessController::initialize_default(const RequestBinding& binding,
                                                     const Activity& activity,
                                                     std::uint64_t now_ms) {
    if (store_.state() != AccessStoreState::Erased)
        return AccessCode::Conflict;
    if (!idle_for_access(activity))
        return AccessCode::Busy;
    const auto permit = consume(binding, false, true, now_ms);
    if (permit != AccessCode::Ok)
        return permit;
    AccessRecord record;
    record.epoch = 1;
    record.password = identity_.default_password;
    if (!store_.initialize(record)) {
        scrub(record);
        return AccessCode::StorageFault;
    }
    scrub(record);
    return AccessCode::Ok;
}

AccessCode LocalAccessController::open_enrollment(const RequestBinding& binding,
                                                  const Activity& activity,
                                                  std::uint64_t now_ms) {
    if (!store_.healthy())
        return AccessCode::StorageFault;
    if (!idle_for_access(activity) || ble_.peer)
        return AccessCode::Busy;
    if (enrollment_open(now_ms))
        return AccessCode::Busy;
    const bool public_default = store_.record()->default_password;
    const auto permit = public_default ? consume(binding, false, true, now_ms)
                                       : consume_either(binding, now_ms);
    if (permit != AccessCode::Ok)
        return permit;
    enrollment_started_ms_ = now_ms;
    enrollment_active_ = true;
    return AccessCode::Ok;
}

bool LocalAccessController::enrollment_open(std::uint64_t now_ms) const {
    return enrollment_active_ && !elapsed(now_ms, enrollment_started_ms_, enrollment_window_ms);
}

bool LocalAccessController::retained_bond(std::uint64_t peer) const {
    if (!store_.record())
        return false;
    return std::find(store_.record()->bonds.begin(),
                     store_.record()->bonds.begin() + store_.record()->bond_count,
                     peer) != store_.record()->bonds.begin() + store_.record()->bond_count;
}

std::string LocalAccessController::bond_principal(std::uint64_t peer) const {
    std::array<char, 16> digits{};
    const auto result = std::to_chars(digits.data(), digits.data() + digits.size(), peer, 16);
    return "ble-" + std::string(digits.data(), result.ptr) + "-" +
           std::to_string(store_.record() ? store_.record()->epoch : 0);
}

BleAdmission LocalAccessController::ble_connect(std::uint64_t peer, bool encrypted,
                                                bool new_pairing, std::string session_id,
                                                std::uint64_t now_ms) {
    if (!store_.healthy())
        return {AccessCode::StorageFault};
    if (!peer || !encrypted || !bounded_text(session_id, 64))
        return {AccessCode::AuthenticationRequired};
    if (store_.record()->ble_disabled)
        return {AccessCode::BondEraseFault};
    if (ble_.peer)
        return {AccessCode::Busy};
    const bool retained = retained_bond(peer);
    if (new_pairing && (!enrollment_open(now_ms) || retained))
        return {AccessCode::AuthenticationRequired};
    if (!new_pairing && !retained)
        return {AccessCode::AuthenticationRequired};
    ble_.peer = peer;
    ble_.session_id = std::move(session_id);
    ble_.encrypted = true;
    ble_.provisional = new_pairing;
    ble_.authorized = retained;
    return {AccessCode::Ok, retained ? bond_principal(peer) : std::string{}, new_pairing};
}

BleAdmission LocalAccessController::ble_authorize(std::string_view password,
                                                  std::uint64_t now_ms) {
    if (!ble_.peer || !ble_.encrypted || !ble_.provisional || !enrollment_open(now_ms))
        return {AccessCode::AuthenticationRequired};
    if (!password_matches(password)) {
        const auto peer = ble_.peer;
        clear_ble();
        if (!bonds_.erase(peer))
            (void)mark_ble_disabled();
        return {AccessCode::AuthenticationRequired};
    }
    if (store_.record()->bond_count >= authorized_bond_capacity) {
        const auto peer = ble_.peer;
        clear_ble();
        if (!bonds_.erase(peer))
            (void)mark_ble_disabled();
        return {AccessCode::Capacity};
    }
    auto replacement = *store_.record();
    replacement.bonds[replacement.bond_count++] = ble_.peer;
    if (!store_.replace(replacement)) {
        const auto peer = ble_.peer;
        scrub(replacement);
        clear_ble();
        if (!bonds_.erase(peer))
            (void)mark_ble_disabled();
        return {AccessCode::StorageFault};
    }
    scrub(replacement);
    ble_.provisional = false;
    ble_.authorized = true;
    enrollment_active_ = false;
    return {AccessCode::Ok, bond_principal(ble_.peer), false};
}

void LocalAccessController::clear_ble() {
    secure_clear(ble_.session_id);
    ble_ = {};
}

bool LocalAccessController::ble_disconnect() {
    const bool provisional = ble_.provisional;
    const auto peer = ble_.peer;
    invalidate_binding(ble_.authorized ? bond_principal(peer) : std::string{}, ble_.session_id);
    clear_ble();
    if (provisional && !bonds_.erase(peer))
        (void)mark_ble_disabled();
    return provisional;
}

bool LocalAccessController::mark_ble_disabled() {
    if (!store_.healthy())
        return false;
    auto replacement = *store_.record();
    replacement.ble_disabled = true;
    const bool result = store_.replace(replacement);
    scrub(replacement);
    return result;
}

AccessCode LocalAccessController::remove_bond(std::uint64_t peer,
                                              const RequestBinding& binding,
                                              const Activity& activity,
                                              std::uint64_t now_ms) {
    if (!store_.healthy())
        return AccessCode::StorageFault;
    if (!idle_for_access(activity))
        return AccessCode::Busy;
    const auto permit = consume(binding, true, store_.record()->default_password, now_ms);
    if (permit != AccessCode::Ok)
        return permit;
    auto replacement = *store_.record();
    auto end = replacement.bonds.begin() + replacement.bond_count;
    auto found = std::find(replacement.bonds.begin(), end, peer);
    if (found == end) {
        scrub(replacement);
        return AccessCode::Invalid;
    }
    std::move(found + 1, end, found);
    replacement.bonds[--replacement.bond_count] = 0;
    if (!store_.replace(replacement)) {
        scrub(replacement);
        return AccessCode::StorageFault;
    }
    scrub(replacement);
    if (ble_.peer == peer)
        clear_ble();
    if (!bonds_.erase(peer)) {
        (void)mark_ble_disabled();
        return AccessCode::BondEraseFault;
    }
    return AccessCode::Ok;
}

void LocalAccessController::clear_session(SoftApSession& session) {
    secure_clear(session.token);
    secure_clear(session.principal);
    secure_clear(session.boot_id);
    secure_clear(session.wtp_session);
    session = {};
}

void LocalAccessController::reclaim(std::uint64_t now_ms, std::string_view protected_wtp_session) {
    for (auto& session : softap_) {
        if (!session.live)
            continue;
        const bool protected_owner =
            !protected_wtp_session.empty() && session.wtp_session == protected_wtp_session;
        if (session.boot_id != boot_id_ || !store_.record() ||
            session.epoch != store_.record()->epoch ||
            (!protected_owner &&
             (elapsed(now_ms, session.created_ms, softap_absolute_ms) ||
              elapsed(now_ms, session.last_activity_ms, softap_inactivity_ms))))
            clear_session(session);
    }
}

LocalAccessController::SoftApSession* LocalAccessController::find_session(std::string_view token) {
    for (auto& session : softap_)
        if (session.live && constant_equal(session.token, token))
            return &session;
    return nullptr;
}

SoftApLogin LocalAccessController::softap_login(std::string_view password, std::uint64_t now_ms,
                                                std::string_view protected_wtp_session) {
    if (!store_.healthy())
        return {AccessCode::StorageFault};
    if (!password_matches(password))
        return {AccessCode::AuthenticationRequired};
    reclaim(now_ms, protected_wtp_session);
    auto slot = std::find_if(softap_.begin(), softap_.end(),
                             [](const SoftApSession& value) { return !value.live; });
    if (slot == softap_.end())
        return {AccessCode::Capacity};
    std::array<std::uint8_t, 16> bytes{};
    if (!random_.fill(bytes))
        return {AccessCode::Invalid};
    auto token = hex(bytes);
    const auto digest = wtp::sha256(bytes);
    std::fill(bytes.begin(), bytes.end(), 0);
    if (find_session(token)) {
        secure_clear(token);
        return {AccessCode::Conflict};
    }
    slot->token = token;
    secure_clear(token);
    slot->principal = "softap-" + hex(std::span(digest).first(12));
    slot->boot_id = boot_id_;
    slot->epoch = store_.record()->epoch;
    slot->created_ms = now_ms;
    slot->last_activity_ms = now_ms;
    slot->live = true;
    return {AccessCode::Ok, slot->token, slot->principal};
}

AccessCode LocalAccessController::bind_softap_session(std::string_view token,
                                                      std::string_view wtp_session,
                                                      std::uint64_t now_ms) {
    if (!bounded_text(wtp_session, 64))
        return AccessCode::Invalid;
    auto* session = find_session(token);
    if (!session)
        return AccessCode::Expired;
    if (session->boot_id != boot_id_ || !store_.record() ||
        session->epoch != store_.record()->epoch ||
        elapsed(now_ms, session->created_ms, softap_absolute_ms) ||
        elapsed(now_ms, session->last_activity_ms, softap_inactivity_ms)) {
        clear_session(*session);
        return AccessCode::Expired;
    }
    if (!session->wtp_session.empty() && session->wtp_session != wtp_session)
        return AccessCode::Conflict;
    session->wtp_session.assign(wtp_session);
    session->last_activity_ms = now_ms;
    return AccessCode::Ok;
}

SoftApAuthority LocalAccessController::softap_authorize(
    std::string_view token, SoftApOperation operation, std::string_view wtp_session,
    std::string_view active_owner_session, const Activity& activity, std::uint64_t now_ms) {
    auto* session = find_session(token);
    if (!session || session->boot_id != boot_id_ || !store_.record() ||
        session->epoch != store_.record()->epoch)
        return {AccessCode::Expired};
    if (!session->wtp_session.empty() && !wtp_session.empty() &&
        session->wtp_session != wtp_session)
        return {AccessCode::Conflict};
    const bool owns_active = activity.owned && (activity.armed || activity.running) &&
                             !session->wtp_session.empty() &&
                             session->wtp_session == active_owner_session;
    const bool absolute = elapsed(now_ms, session->created_ms, softap_absolute_ms);
    if (absolute) {
        if (!owns_active || !grace_operation(operation)) {
            clear_session(*session);
            return {AccessCode::Expired};
        }
        return {AccessCode::Ok, session->principal, true, session->wtp_session};
    }
    if (!owns_active && elapsed(now_ms, session->last_activity_ms, softap_inactivity_ms)) {
        clear_session(*session);
        return {AccessCode::Expired};
    }
    session->last_activity_ms = now_ms;
    return {AccessCode::Ok, session->principal, false, session->wtp_session};
}

AccessCode LocalAccessController::softap_logout(std::string_view token,
                                                std::string_view wtp_session,
                                                std::string_view active_owner_session,
                                                const Activity& activity, std::uint64_t now_ms) {
    auto* session = find_session(token);
    if (!session)
        return AccessCode::Expired;
    if (!session->wtp_session.empty() && session->wtp_session != wtp_session)
        return AccessCode::Conflict;
    const bool owns = activity.owned && !session->wtp_session.empty() &&
                      session->wtp_session == active_owner_session;
    if (owns)
        return AccessCode::Busy;
    if (proof_.active && proof_.binding.principal == session->principal)
        proof_ = {};
    clear_session(*session);
    (void)now_ms;
    return AccessCode::Ok;
}

std::size_t LocalAccessController::live_softap_sessions(std::uint64_t now_ms,
                                                        std::string_view protected_wtp_session) {
    reclaim(now_ms, protected_wtp_session);
    return static_cast<std::size_t>(std::count_if(
        softap_.begin(), softap_.end(), [](const SoftApSession& value) { return value.live; }));
}

AccessCode LocalAccessController::change_password(std::string_view replacement,
                                                  const RequestBinding& binding,
                                                  const Activity& activity,
                                                  std::uint64_t now_ms) {
    if (!store_.healthy())
        return AccessCode::StorageFault;
    if (!idle_for_access(activity))
        return AccessCode::Busy;
    if (!valid_local_password(replacement))
        return AccessCode::Invalid;
    const auto permit = consume(binding, true, store_.record()->default_password, now_ms);
    if (permit != AccessCode::Ok)
        return permit;
    auto changed = *store_.record();
    if (changed.epoch == std::numeric_limits<std::uint64_t>::max()) {
        scrub(changed);
        return AccessCode::Conflict;
    }
    ++changed.epoch;
    secure_clear(changed.password);
    changed.password.assign(replacement);
    changed.default_password = false;
    changed.bonds.fill(0);
    changed.bond_count = 0;
    changed.ble_disabled = false;
    if (!store_.replace(changed)) {
        scrub(changed);
        return AccessCode::StorageFault;
    }
    scrub(changed);
    invalidate_all_volatile();
    if (!bonds_.erase_all()) {
        (void)mark_ble_disabled();
        return AccessCode::BondEraseFault;
    }
    return AccessCode::Ok;
}

AccessCode LocalAccessController::set_field_mode(bool enabled,
                                                 const RequestBinding& binding,
                                                 const Activity& activity,
                                                 std::uint64_t now_ms) {
    if (!store_.healthy())
        return AccessCode::StorageFault;
    if (!idle_for_access(activity))
        return AccessCode::Busy;
    const auto permit =
        consume(binding, true, store_.record()->default_password, now_ms);
    if (permit != AccessCode::Ok)
        return permit;
    auto changed = *store_.record();
    changed.field_mode = enabled;
    if (!store_.replace(changed)) {
        scrub(changed);
        return AccessCode::StorageFault;
    }
    scrub(changed);
    return AccessCode::Ok;
}

void LocalAccessController::invalidate_all_volatile() {
    proof_ = {};
    clear_ble();
    for (auto& session : softap_)
        clear_session(session);
    enrollment_active_ = false;
    enrollment_started_ms_ = 0;
}

std::string LocalAccessController::cookie_header(std::string_view token) {
    if (token.size() != 32 || !std::all_of(token.begin(), token.end(), [](char value) {
            return (value >= '0' && value <= '9') || (value >= 'a' && value <= 'f');
        }))
        return {};
    return "__Host-wsprrypico=" + std::string(token) +
           "; Path=/; Secure; HttpOnly; SameSite=Strict";
}

Authorization LocalAccessController::ble_authorization() const {
    if (!ble_.authorized || !ble_.encrypted || !store_.record() ||
        !retained_bond(ble_.peer) || store_.record()->ble_disabled)
        return {};
    return {true, true, true, bond_principal(ble_.peer)};
}
} // namespace wsprrypico::provisioning
