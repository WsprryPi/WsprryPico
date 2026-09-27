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
}
