#pragma once

#include "network/http.hpp"
#include "provisioning/storage.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
class RuntimeProfile;
}

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

// A TCP ACK of an older checking reply is not delivery of a committed result.
// Snapshot matches() when constructing the response, then report full delivery.
class OwnerResultRestart {
  public:
    void begin(std::uint64_t generation, std::string_view digest, std::uint64_t now_ms);
    bool matches(provisioning::ProfileSource source, std::uint64_t generation,
                 std::string_view digest) const;
    void delivered(bool committed_reply, std::uint64_t now_ms);
    bool ready(std::uint64_t now_ms) const;

  private:
    std::array<char, 64> digest_{};
    std::uint64_t generation_ = 0, committed_ms_ = 0, delivered_ms_ = 0;
    bool pending_ = false, delivered_ = false, digest_valid_ = false;
};

bool owner_public_get_admitted(const HttpRequest& request, std::string_view route);
// Public AP readback of the selected generation's station fields only.
// A stale boot snapshot, fault, wrong device or non-consumer source returns null.
std::string owner_saved_station_json(const provisioning::ProfileStore& store,
                                     const provisioning::RuntimeProfile& runtime,
                                     std::string_view device_id);
// Public AP readback of SSID and time server only; never returns credentials.
std::string owner_saved_network_json(const provisioning::ProfileStore& store,
                                     const provisioning::RuntimeProfile& runtime,
                                     std::string_view device_id);
std::optional<OwnerIdentifyRequest> parse_owner_identify(const HttpRequest& request);
std::optional<OwnerClaimStartRequest> parse_owner_claim_start(const HttpRequest& request);
std::optional<OwnerClaimSubmitRequest> parse_owner_claim_submit(const HttpRequest& request);
} // namespace wsprrypico::network
