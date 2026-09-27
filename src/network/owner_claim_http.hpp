#pragma once

#include "network/http.hpp"
#include "provisioning/storage.hpp"

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::network {
struct OwnerClaimStartRequest {
    std::string device_id, owner_public_key, browser_public_key, browser_nonce;
    provisioning::ProfileSource source = provisioning::ProfileSource::LegacyBootstrap;
    std::uint64_t generation = 0;
};
struct OwnerClaimSubmitRequest {
    std::string device_id, boot_id, slot_id, request_id;
    std::string aead_nonce, ciphertext, tag;
};
struct OwnerIdentifyRequest {
    std::string device_id, boot_id, request_id;
};

bool owner_public_get_admitted(const HttpRequest& request, std::string_view route);
std::optional<OwnerIdentifyRequest> parse_owner_identify(const HttpRequest& request);
std::optional<OwnerClaimStartRequest> parse_owner_claim_start(const HttpRequest& request);
std::optional<OwnerClaimSubmitRequest> parse_owner_claim_submit(const HttpRequest& request);
} // namespace wsprrypico::network
