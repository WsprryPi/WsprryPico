#include "network/owner_wire.hpp"

#include "encoding/wspr.hpp"
#include "standalone/config.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace wsprrypico::network {
namespace {
constexpr std::array<OwnerRoute, 9> routes{{
    {OwnerOperation::Readback, "POST", "/api/owner/v1/readback"},
    {OwnerOperation::OwnerPropose, "POST", "/api/owner/v1/owners/propose"},
    {OwnerOperation::OwnerApprove, "POST", "/api/owner/v1/owners/approve"},
    {OwnerOperation::OwnerRemove, "POST", "/api/owner/v1/owners/remove"},
    {OwnerOperation::ClientEnroll, "POST", "/api/owner/v1/clients/enroll"},
    {OwnerOperation::ClientRevoke, "POST", "/api/owner/v1/clients/revoke"},
    {OwnerOperation::NetworkReplace, "POST", "/api/owner/v1/network/replace"},
    {OwnerOperation::ServerRenew, "POST", "/api/owner/v1/trust/renew"},
    {OwnerOperation::ResetIntent, "POST", "/api/owner/v1/reset/intent"},
}};
constexpr char prefix[] = "WsprryPico/Owner-HTTP/1";
constexpr char session_start_prefix[] = "WsprryPico/Owner-Session-Start/1";
constexpr char session_prefix[] = "WsprryPico/Owner-Session/1";
constexpr char session_finish_prefix[] = "WsprryPico/Owner-Session-Finish/1";
constexpr char claim_prefix[] = "WsprryPico/Owner-Claim/1";
constexpr char claim_origin[] = "http://192.168.4.1";

template <typename T> bool nonzero(const T& bytes) {
    return std::any_of(bytes.begin(), bytes.end(), [](std::uint8_t byte) { return byte != 0; });
}

void update(wtp::Sha256& hash, const void* data, std::size_t size) {
    hash.update({static_cast<const std::uint8_t*>(data), size});
}
void update_u64(wtp::Sha256& hash, std::uint64_t value) {
    std::array<std::uint8_t, 8> bytes{};
    for (int i = 7; i >= 0; --i) {
        bytes[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>(value);
        value >>= 8;
    }
    hash.update(bytes);
}
void update_text(wtp::Sha256& hash, std::string_view text) {
    update(hash, text.data(), text.size());
}

bool valid_session_start(const OwnerSessionFields& fields) {
    return nonzero(fields.device_id) && nonzero(fields.owner_key_sha256) &&
           nonzero(fields.browser_public_key) && nonzero(fields.browser_nonce);
}

bool valid_session(const OwnerSessionFields& fields) {
    return valid_session_start(fields) && nonzero(fields.boot_id) && fields.owner_epoch &&
           fields.profile_generation && nonzero(fields.session_id) &&
           nonzero(fields.pico_public_key) && nonzero(fields.pico_challenge) &&
           fields.expiry_monotonic_ms;
}

void update_session(wtp::Sha256& hash, const OwnerSessionFields& fields) {
    update(hash, session_prefix, sizeof(session_prefix));
    hash.update(fields.device_id);
    hash.update(fields.boot_id);
    hash.update(fields.owner_key_sha256);
    update_u64(hash, fields.owner_epoch);
    update_u64(hash, fields.profile_generation);
    hash.update(fields.session_id);
    hash.update(fields.browser_public_key);
    hash.update(fields.pico_public_key);
    hash.update(fields.browser_nonce);
    hash.update(fields.pico_challenge);
    update_u64(hash, fields.expiry_monotonic_ms);
}
} // namespace

std::optional<OwnerRoute> owner_route(OwnerOperation operation) {
    for (const auto& route : routes) {
        if (route.operation == operation)
            return route;
    }
    return std::nullopt;
}

std::optional<wtp::PayloadDigest> owner_signing_digest(const OwnerSigningFields& fields) {
    const auto route = owner_route(fields.operation);
    const std::size_t maximum_body = fields.operation == OwnerOperation::ClientEnroll ? 2048 : 1024;
    if (!route || fields.method != route->method || fields.path != route->path ||
        !fields.owner_epoch || !fields.profile_generation || !fields.expiry_monotonic_ms ||
        !nonzero(fields.device_id) || !nonzero(fields.boot_id) || !nonzero(fields.request_id) ||
        !nonzero(fields.challenge) || fields.sealed_body.size() < 16 ||
        fields.sealed_body.size() > maximum_body)
        return std::nullopt;

    // Body digest is over exact decoded ciphertext || tag. A caller cannot
    // substitute JSON whitespace, property order, or a claimed body hash.
    wtp::Sha256 body;
    update_text(body, fields.method);
    const std::uint8_t zero = 0;
    body.update({&zero, 1});
    update_text(body, fields.path);
    body.update({&zero, 1});
    body.update(fields.sealed_body);
    const auto body_digest = body.finish();

    wtp::Sha256 signing;
    update(signing, prefix, sizeof(prefix)); // Includes the required NUL.
    const auto operation = static_cast<std::uint8_t>(fields.operation);
    signing.update({&operation, 1});
    signing.update(fields.device_id);
    signing.update(fields.boot_id);
    update_u64(signing, fields.owner_epoch);
    update_u64(signing, fields.profile_generation);
    signing.update(fields.request_id);
    signing.update(fields.challenge);
    update_u64(signing, fields.expiry_monotonic_ms);
    signing.update(body_digest);
    return signing.finish();
}

std::optional<wtp::PayloadDigest> owner_session_start_digest(const OwnerSessionFields& fields) {
    if (!valid_session_start(fields))
        return std::nullopt;
    wtp::Sha256 hash;
    update(hash, session_start_prefix, sizeof(session_start_prefix));
    hash.update(fields.device_id);
    hash.update(fields.owner_key_sha256);
    hash.update(fields.browser_public_key);
    hash.update(fields.browser_nonce);
    return hash.finish();
}

std::optional<wtp::PayloadDigest> owner_session_finish_digest(const OwnerSessionFields& fields) {
    if (!valid_session(fields))
        return std::nullopt;
    const auto start = owner_session_start_digest(fields);
    if (!start)
        return std::nullopt;
    wtp::Sha256 hash;
    update(hash, session_finish_prefix, sizeof(session_finish_prefix));
    update_session(hash, fields);
    hash.update(*start);
    return hash.finish();
}

std::optional<wtp::PayloadDigest> owner_session_salt(const OwnerSessionFields& fields) {
    if (!valid_session(fields))
        return std::nullopt;
    wtp::Sha256 hash;
    update_session(hash, fields);
    return hash.finish();
}

std::optional<OwnerClaimTranscript> owner_claim_transcript(const OwnerClaimFields& fields) {
    const bool claimable =
        (fields.source == provisioning::ProfileSource::LegacyBootstrap && fields.generation == 0) ||
        ((fields.source == provisioning::ProfileSource::Unprovisioned ||
          fields.source == provisioning::ProfileSource::NetworkOnly) &&
         fields.generation > 0 && fields.generation < UINT64_MAX);
    if (!claimable || !nonzero(fields.device_id) || !nonzero(fields.boot_id) ||
        !nonzero(fields.slot_id) || fields.owner_public_key[0] != 4 ||
        !nonzero(fields.browser_public_key) || !nonzero(fields.pico_public_key) ||
        !nonzero(fields.browser_nonce) || !nonzero(fields.request_id))
        return std::nullopt;

    OwnerClaimTranscript result;
    auto append = [&](const void* bytes, std::size_t size) {
        if (size > result.bytes.size() - result.size)
            return false;
        std::memcpy(result.bytes.data() + result.size, bytes, size);
        result.size += size;
        return true;
    };
    const auto source = static_cast<std::uint8_t>(fields.source);
    std::array<std::uint8_t, 8> generation{};
    auto value = fields.generation;
    for (int i = 7; i >= 0; --i) {
        generation[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>(value);
        value >>= 8;
    }
    if (!append(claim_prefix, sizeof(claim_prefix)) ||
        !append(fields.device_id.data(), fields.device_id.size()) ||
        !append(fields.boot_id.data(), fields.boot_id.size()) ||
        !append(fields.slot_id.data(), fields.slot_id.size()) ||
        !append(claim_origin, sizeof(claim_origin) - 1) || !append(&source, 1) ||
        !append(generation.data(), generation.size()) ||
        !append(fields.owner_public_key.data(), fields.owner_public_key.size()) ||
        !append(fields.browser_public_key.data(), fields.browser_public_key.size()) ||
        !append(fields.pico_public_key.data(), fields.pico_public_key.size()) ||
        !append(fields.browser_nonce.data(), fields.browser_nonce.size()) ||
        !append(fields.request_id.data(), fields.request_id.size()))
        return std::nullopt;
    return result;
}

std::optional<OwnerClaimEncodedPlaintext>
encode_owner_claim_plaintext(const OwnerClaimPlaintext& value) {
    const bool saved_network = value.ssid.empty() && value.password.empty();
    if ((!saved_network &&
         !standalone::valid_wifi_credentials(value.ssid, value.password,
                                             standalone::default_time_server)) ||
        !encoding::wspr_type1(value.callsign, value.locator, value.power_dbm))
        return std::nullopt;
    OwnerClaimEncodedPlaintext result;
    auto append_text = [&](std::string_view part) {
        result.bytes[result.size++] = static_cast<std::uint8_t>(part.size());
        std::memcpy(result.bytes.data() + result.size, part.data(), part.size());
        result.size += part.size();
    };
    append_text(value.ssid);
    append_text(value.password);
    append_text(value.callsign);
    std::memcpy(result.bytes.data() + result.size, value.locator.data(), 4);
    result.size += 4;
    result.bytes[result.size++] = static_cast<std::uint8_t>(value.power_dbm);
    return result;
}

std::optional<OwnerClaimPlaintext>
decode_owner_claim_plaintext(std::span<const std::uint8_t> bytes) {
    if (bytes.size() < 11 || bytes.size() > 109)
        return std::nullopt;
    std::size_t at = 0;
    auto read_text = [&](std::size_t minimum, std::size_t maximum, std::string_view& out) {
        if (at >= bytes.size())
            return false;
        const auto size = bytes[at++];
        if (size < minimum || size > maximum || size > bytes.size() - at)
            return false;
        out = {reinterpret_cast<const char*>(bytes.data() + at), size};
        at += size;
        return true;
    };
    OwnerClaimPlaintext result;
    if (!read_text(0, 32, result.ssid) || !read_text(0, 63, result.password) ||
        !read_text(3, 6, result.callsign) || bytes.size() - at != 5)
        return std::nullopt;
    result.locator = {reinterpret_cast<const char*>(bytes.data() + at), 4};
    at += 4;
    result.power_dbm = bytes[at];
    const bool saved_network = result.ssid.empty() && result.password.empty();
    if ((!saved_network &&
         !standalone::valid_wifi_credentials(result.ssid, result.password,
                                             standalone::default_time_server)) ||
        !encoding::wspr_type1(result.callsign, result.locator, result.power_dbm))
        return std::nullopt;
    return result;
}

} // namespace wsprrypico::network
