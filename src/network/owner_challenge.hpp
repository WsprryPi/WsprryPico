#pragma once

#include "network/owner_wire.hpp"

#include <array>
#include <cstdint>

namespace wsprrypico::network {

struct OwnerChallengeBinding {
    OwnerOperation operation = OwnerOperation::Readback;
    std::array<std::uint8_t, 16> device_id{};
    std::array<std::uint8_t, 16> boot_id{};
    std::array<std::uint8_t, 16> session_id{};
    std::array<std::uint8_t, 32> owner_key_sha256{};
    std::uint64_t owner_epoch = 0;
    std::uint64_t profile_generation = 0;
    std::array<std::uint8_t, 16> request_id{};
    std::array<std::uint8_t, 16> challenge{};
    std::uint64_t expiry_monotonic_ms = 0;
    bool operator==(const OwnerChallengeBinding&) const = default;
};

// Single pending challenge. take() consumes it before signature verification,
// including an invalid submission. The caller must validate current journal,
// output and session state, then verify the exact signing digest and signature.
class OwnerChallengeSlot {
  public:
    static constexpr std::uint64_t maximum_window_ms = 30'000;
    OwnerChallengeSlot() = default;
    ~OwnerChallengeSlot() {
        cancel();
    }
    OwnerChallengeSlot(const OwnerChallengeSlot&) = delete;
    OwnerChallengeSlot& operator=(const OwnerChallengeSlot&) = delete;

    bool issue(const OwnerChallengeBinding& binding, std::uint64_t now_ms);
    std::optional<wtp::PayloadDigest> take(const OwnerSigningFields& signed_fields,
                                           const std::array<std::uint8_t, 16>& session_id,
                                           const std::array<std::uint8_t, 32>& owner_key_sha256,
                                           std::uint64_t now_ms);
    void cancel();
    bool pending() const {
        return pending_;
    }

  private:
    OwnerChallengeBinding binding_{};
    std::uint64_t issued_ms_ = 0;
    bool pending_ = false;
};

} // namespace wsprrypico::network
