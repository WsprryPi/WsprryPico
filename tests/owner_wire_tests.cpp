#include "network/bootstrap_codec.hpp"
#include "network/owner_wire.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <string>

using namespace wsprrypico;

int main() {
    std::array<std::uint8_t, 20> body{};
    body[0] = 1;
    body[1] = 2;
    body[2] = 3;
    body[3] = 4;
    for (std::size_t i = 4; i < body.size(); ++i)
        body[i] = static_cast<std::uint8_t>(0xa0 + i - 4);

    network::OwnerSigningFields fields;
    fields.operation = network::OwnerOperation::NetworkReplace;
    fields.method = "POST";
    fields.path = "/api/owner/v1/network/replace";
    for (std::size_t i = 0; i < 16; ++i) {
        fields.device_id[i] = static_cast<std::uint8_t>(i);
        fields.boot_id[i] = static_cast<std::uint8_t>(i + 16);
        fields.request_id[i] = static_cast<std::uint8_t>(i + 32);
        fields.challenge[i] = static_cast<std::uint8_t>(i + 48);
    }
    fields.owner_epoch = 5;
    fields.profile_generation = 9;
    fields.expiry_monotonic_ms = 123456789;
    fields.sealed_body = body;

    // Independently computed with Python hashlib/struct, not this C++ SHA.
    constexpr auto expected = "2d7abd422c7760352607cf9521a840535e4610b19f11536c0fbfde7338dc337f";
    const auto digest = network::owner_signing_digest(fields);
    assert(digest && network::bootstrap_hex(*digest) == expected);
    auto changed = fields;
    changed.device_id[0] ^= 1;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    changed.boot_id[0] ^= 1;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    ++changed.owner_epoch;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    ++changed.profile_generation;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    changed.request_id[0] ^= 1;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    changed.challenge[0] ^= 1;
    assert(network::owner_signing_digest(changed) != digest);
    changed = fields;
    ++changed.expiry_monotonic_ms;
    assert(network::owner_signing_digest(changed) != digest);
    body[0] ^= 1;
    assert(network::owner_signing_digest(fields) != digest);
    body[0] ^= 1;

    changed = fields;
    changed.operation = network::OwnerOperation::ServerRenew;
    assert(!network::owner_signing_digest(changed)); // Route/op mismatch.
    changed = fields;
    changed.method = "GET";
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.path = "/api/owner/v1/network/replace/";
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.operation = static_cast<network::OwnerOperation>(0xff);
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.owner_epoch = 0;
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.profile_generation = 0;
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.expiry_monotonic_ms = 0;
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.challenge.fill(0);
    assert(!network::owner_signing_digest(changed));
    changed = fields;
    changed.sealed_body = std::span(body).first<15>();
    assert(!network::owner_signing_digest(changed));
    std::array<std::uint8_t, 1025> oversized{};
    changed.sealed_body = oversized;
    assert(!network::owner_signing_digest(changed));
    changed.operation = network::OwnerOperation::ClientEnroll;
    changed.path = "/api/owner/v1/clients/enroll";
    assert(network::owner_signing_digest(changed));
    std::array<std::uint8_t, 2049> oversized_csr{};
    changed.sealed_body = oversized_csr;
    assert(!network::owner_signing_digest(changed));
    const auto route = network::owner_route(network::OwnerOperation::NetworkReplace);
    assert(route && route->method == "POST" && route->path == fields.path);
    assert(!network::owner_route(static_cast<network::OwnerOperation>(0xff)));

    network::OwnerSessionFields session;
    for (std::size_t i = 0; i < 16; ++i) {
        session.device_id[i] = static_cast<std::uint8_t>(i);
        session.boot_id[i] = static_cast<std::uint8_t>(i + 16);
        session.session_id[i] = static_cast<std::uint8_t>(i + 64);
        session.browser_nonce[i] = static_cast<std::uint8_t>(i + 144);
        session.pico_challenge[i] = static_cast<std::uint8_t>(i + 160);
    }
    for (std::size_t i = 0; i < 32; ++i) {
        session.owner_key_sha256[i] = static_cast<std::uint8_t>(i + 32);
        session.browser_public_key[i] = static_cast<std::uint8_t>(i + 80);
        session.pico_public_key[i] = static_cast<std::uint8_t>(i + 112);
    }
    session.owner_epoch = 5;
    session.profile_generation = 9;
    session.expiry_monotonic_ms = 123456789;
    // Independent Python hashlib/struct vectors for exact binary transcripts.
    const auto start_digest = network::owner_session_start_digest(session);
    const auto finish_digest = network::owner_session_finish_digest(session);
    const auto salt = network::owner_session_salt(session);
    assert(start_digest && network::bootstrap_hex(*start_digest) ==
                               "d9ae570529415c35a6b879873740fbc6d283202f08191d2d0c7a931307ec4396");
    assert(finish_digest && network::bootstrap_hex(*finish_digest) ==
                                "3f2463922847a96b5b3e21fbf668203fa54e7ec10a80206452809e34db787131");
    assert(salt && network::bootstrap_hex(*salt) ==
                       "bea5a3bb64ef326c01a1339bc042f7ea0714f533ec9032d82309e148a047bfdc");
    auto start_only = session;
    start_only.boot_id = {};
    start_only.pico_public_key = {};
    start_only.pico_challenge = {};
    start_only.session_id = {};
    start_only.owner_epoch = 0;
    start_only.profile_generation = 0;
    start_only.expiry_monotonic_ms = 0;
    assert(network::owner_session_start_digest(start_only) == start_digest);
    assert(!network::owner_session_finish_digest(start_only));
    auto changed_session = session;
    changed_session.device_id[0] ^= 1;
    assert(network::owner_session_start_digest(changed_session) != start_digest);
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.boot_id[0] ^= 1;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.owner_key_sha256[0] ^= 1;
    assert(network::owner_session_start_digest(changed_session) != start_digest);
    assert(network::owner_session_salt(changed_session) != salt);
    changed_session = session;
    changed_session.session_id[0] ^= 1;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.browser_public_key[0] ^= 1;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.pico_public_key[0] ^= 1;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.browser_nonce[0] ^= 1;
    assert(network::owner_session_start_digest(changed_session) != start_digest);
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.pico_challenge[0] ^= 1;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    ++changed_session.owner_epoch;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    ++changed_session.profile_generation;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    ++changed_session.expiry_monotonic_ms;
    assert(network::owner_session_finish_digest(changed_session) != finish_digest);
    changed_session = session;
    changed_session.owner_epoch = 0;
    assert(network::owner_session_start_digest(changed_session) == start_digest);
    assert(!network::owner_session_finish_digest(changed_session));

    network::OwnerClaimFields claim;
    for (std::size_t i = 0; i < 16; ++i) {
        claim.device_id[i] = static_cast<std::uint8_t>(i + 1);
        claim.boot_id[i] = static_cast<std::uint8_t>(i + 17);
        claim.slot_id[i] = static_cast<std::uint8_t>(i + 33);
        claim.browser_nonce[i] = static_cast<std::uint8_t>(i + 113);
        claim.request_id[i] = static_cast<std::uint8_t>(i + 129);
    }
    for (std::size_t i = 0; i < 32; ++i) {
        claim.browser_public_key[i] = static_cast<std::uint8_t>(i + 49);
        claim.pico_public_key[i] = static_cast<std::uint8_t>(i + 81);
    }
    assert(network::bootstrap_unhex(
        "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c2964fe342e2fe1a7f9b8ee7eb4a"
        "7c0f9e162bce33576b315ececbb6406837bf51f5",
        claim.owner_public_key));
    claim.source = provisioning::ProfileSource::NetworkOnly;
    claim.generation = 1;
    const auto transcript = network::owner_claim_transcript(claim);
    assert(transcript && transcript->size == 261);
    assert(network::bootstrap_digest(transcript->view()) ==
           "b13fd05696af4d82e4684aacdde110cefbfe3918a65b3da56dc4451f020d988f");
    const auto claim_differs = [&](const network::OwnerClaimFields& candidate) {
        const auto other = network::owner_claim_transcript(candidate);
        return other && network::bootstrap_digest(other->view()) !=
                            network::bootstrap_digest(transcript->view());
    };
    auto changed_claim = claim;
    changed_claim.device_id[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.boot_id[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.slot_id[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.owner_public_key[1] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.browser_public_key[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.pico_public_key[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.browser_nonce[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.request_id[0] ^= 1;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.generation = 2;
    assert(claim_differs(changed_claim));
    changed_claim = claim;
    changed_claim.source = provisioning::ProfileSource::Unprovisioned;
    assert(claim_differs(changed_claim));
    changed_claim.source = provisioning::ProfileSource::ConsumerProfile;
    assert(!network::owner_claim_transcript(changed_claim));
    changed_claim = claim;
    changed_claim.owner_public_key[0] = 0;
    assert(!network::owner_claim_transcript(changed_claim));

    const network::OwnerClaimPlaintext value{"LabNet", "test-only-password", "K1ABC", "FN20", 30};
    const auto encoded = network::encode_owner_claim_plaintext(value);
    assert(encoded && encoded->size == 37);
    assert(network::bootstrap_hex(encoded->view()) ==
           "064c61624e657412746573742d6f6e6c792d70617373776f7264054b31414243464e32301e");
    const auto decoded = network::decode_owner_claim_plaintext(encoded->view());
    assert(decoded && decoded->ssid == value.ssid && decoded->password == value.password &&
           decoded->callsign == value.callsign && decoded->locator == value.locator &&
           decoded->power_dbm == value.power_dbm);
    auto malformed = *encoded;
    malformed.bytes[0] = 33;
    assert(!network::decode_owner_claim_plaintext(malformed.view()));
    malformed = *encoded;
    malformed.bytes[malformed.size - 1] = 31;
    assert(!network::decode_owner_claim_plaintext(malformed.view()));
    malformed = *encoded;
    malformed.bytes[malformed.size++] = 0;
    assert(!network::decode_owner_claim_plaintext(malformed.view()));
    assert(!network::encode_owner_claim_plaintext({"LabNet", "short", "K1ABC", "FN20", 30}));
    const auto maximum = network::encode_owner_claim_plaintext(
        {std::string(32, 'A'), std::string(63, 'p'), "KA1BCD", "FN20", 60});
    assert(maximum && maximum->size == 109);
    assert(network::decode_owner_claim_plaintext(maximum->view()));
    const auto minimum = network::encode_owner_claim_plaintext({"a", "12345678", "K1A", "AA00", 0});
    assert(minimum && minimum->size == 20);
    assert(network::decode_owner_claim_plaintext(minimum->view()));
}
