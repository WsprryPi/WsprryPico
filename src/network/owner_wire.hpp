#pragma once

#include "provisioning/storage.hpp"
#include "wtp/sha256.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace wsprrypico::network {

// Registry values are wire-stable within Owner-HTTP/1. A route must compare
// both the operation number and the exact method/path before signature use.
enum class OwnerOperation : std::uint8_t {
    Readback = 0x10,
    OwnerPropose = 0x11,
    OwnerApprove = 0x12,
    OwnerRemove = 0x13,
    ClientEnroll = 0x20,
    ClientRevoke = 0x21,
    NetworkReplace = 0x30,
    ServerRenew = 0x31,
    ResetIntent = 0x40,
};

struct OwnerRoute {
    OwnerOperation operation;
    std::string_view method;
    std::string_view path;
};

std::optional<OwnerRoute> owner_route(OwnerOperation operation);

struct OwnerSigningFields {
    OwnerOperation operation = OwnerOperation::Readback;
    std::string_view method;
    std::string_view path;
    std::array<std::uint8_t, 16> device_id{};
    std::array<std::uint8_t, 16> boot_id{};
    std::uint64_t owner_epoch = 0;
    std::uint64_t profile_generation = 0;
    std::array<std::uint8_t, 16> request_id{};
    std::array<std::uint8_t, 16> challenge{};
    std::uint64_t expiry_monotonic_ms = 0;
    // Exact decoded ciphertext followed by its decoded 16-byte tag.
    std::span<const std::uint8_t> sealed_body;
};

// Returns SHA-256 of the canonical binary signing input. This only constructs
// bytes: it does not verify an owner key, issue a challenge or grant authority.
std::optional<wtp::PayloadDigest> owner_signing_digest(const OwnerSigningFields& fields);

// Canonical session/start, finish-signature and HKDF-salt inputs. These
// portable builders do not authenticate an owner or create a live session.
struct OwnerSessionFields {
    std::array<std::uint8_t, 16> device_id{};
    std::array<std::uint8_t, 16> boot_id{};
    std::array<std::uint8_t, 32> owner_key_sha256{};
    std::uint64_t owner_epoch = 0;
    std::uint64_t profile_generation = 0;
    std::array<std::uint8_t, 16> session_id{};
    std::array<std::uint8_t, 32> browser_public_key{};
    std::array<std::uint8_t, 32> pico_public_key{};
    std::array<std::uint8_t, 16> browser_nonce{};
    std::array<std::uint8_t, 16> pico_challenge{};
    std::uint64_t expiry_monotonic_ms = 0;
};

std::optional<wtp::PayloadDigest> owner_session_start_digest(const OwnerSessionFields& fields);
std::optional<wtp::PayloadDigest> owner_session_finish_digest(const OwnerSessionFields& fields);
std::optional<wtp::PayloadDigest> owner_session_salt(const OwnerSessionFields& fields);

// Claim AEAD AAD is the complete fixed-order transcript. The caller must
// validate the P-256 point and X25519 exchange, bind these fields to the live
// claim slot and current journal, and consume the slot before a trial.
struct OwnerClaimFields {
    std::array<std::uint8_t, 16> device_id{}, boot_id{}, slot_id{};
    std::array<std::uint8_t, 65> owner_public_key{};
    std::array<std::uint8_t, 32> browser_public_key{}, pico_public_key{};
    std::array<std::uint8_t, 16> browser_nonce{}, request_id{};
    provisioning::ProfileSource source = provisioning::ProfileSource::LegacyBootstrap;
    std::uint64_t generation = 0;
};

struct OwnerClaimTranscript {
    std::array<std::uint8_t, 320> bytes{};
    std::size_t size = 0;
    std::span<const std::uint8_t> view() const {
        return {bytes.data(), size};
    }
};

std::optional<OwnerClaimTranscript> owner_claim_transcript(const OwnerClaimFields& fields);

// This compact plaintext is encrypted in its entirety. Views returned by the
// decoder alias caller-owned decrypted storage; clear that storage after use.
struct OwnerClaimPlaintext {
    std::string_view ssid, password, callsign, locator;
    unsigned power_dbm = 0;
};
struct OwnerClaimEncodedPlaintext {
    std::array<std::uint8_t, 109> bytes{};
    std::size_t size = 0;
    ~OwnerClaimEncodedPlaintext() {
        volatile std::uint8_t* writable = bytes.data();
        for (std::size_t i = 0; i < bytes.size(); ++i)
            writable[i] = 0;
        size = 0;
    }
    std::span<const std::uint8_t> view() const {
        return {bytes.data(), size};
    }
};
std::optional<OwnerClaimEncodedPlaintext>
encode_owner_claim_plaintext(const OwnerClaimPlaintext& value);
std::optional<OwnerClaimPlaintext>
decode_owner_claim_plaintext(std::span<const std::uint8_t> bytes);

} // namespace wsprrypico::network
