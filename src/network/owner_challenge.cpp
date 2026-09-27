#include "network/owner_challenge.hpp"

#include <algorithm>

namespace wsprrypico::network {
namespace {
template <typename T> bool nonzero(const T& bytes) {
    return std::any_of(bytes.begin(), bytes.end(), [](std::uint8_t byte) { return byte != 0; });
}
} // namespace

bool OwnerChallengeSlot::issue(const OwnerChallengeBinding& binding, std::uint64_t now_ms) {
    if (pending_ && now_ms < issued_ms_) {
        cancel();
        return false;
    }
    if (pending_ && now_ms >= binding_.expiry_monotonic_ms)
        cancel();
    if (pending_ || !owner_route(binding.operation) || !nonzero(binding.device_id) ||
        !nonzero(binding.boot_id) || !nonzero(binding.session_id) ||
        !nonzero(binding.owner_key_sha256) || !nonzero(binding.request_id) ||
        !nonzero(binding.challenge) || !binding.owner_epoch || !binding.profile_generation ||
        binding.expiry_monotonic_ms <= now_ms ||
        binding.expiry_monotonic_ms - now_ms > maximum_window_ms)
        return false;
    binding_ = binding;
    issued_ms_ = now_ms;
    pending_ = true;
    return true;
}

std::optional<wtp::PayloadDigest> OwnerChallengeSlot::take(
    const OwnerSigningFields& signed_fields, const std::array<std::uint8_t, 16>& session_id,
    const std::array<std::uint8_t, 32>& owner_key_sha256, std::uint64_t now_ms) {
    if (!pending_)
        return std::nullopt;
    const auto digest = owner_signing_digest(signed_fields);
    OwnerChallengeBinding current;
    current.operation = signed_fields.operation;
    current.device_id = signed_fields.device_id;
    current.boot_id = signed_fields.boot_id;
    current.session_id = session_id;
    current.owner_key_sha256 = owner_key_sha256;
    current.owner_epoch = signed_fields.owner_epoch;
    current.profile_generation = signed_fields.profile_generation;
    current.request_id = signed_fields.request_id;
    current.challenge = signed_fields.challenge;
    current.expiry_monotonic_ms = signed_fields.expiry_monotonic_ms;
    const bool match = digest && now_ms >= issued_ms_ && now_ms < binding_.expiry_monotonic_ms &&
                       current == binding_;
    cancel(); // First complete attempt burns the ticket even when mismatched.
    return match ? digest : std::nullopt;
}

void OwnerChallengeSlot::cancel() {
    volatile std::uint8_t* bytes = reinterpret_cast<volatile std::uint8_t*>(&binding_);
    for (std::size_t i = 0; i < sizeof(binding_); ++i)
        bytes[i] = 0;
    binding_ = {};
    issued_ms_ = 0;
    pending_ = false;
}

} // namespace wsprrypico::network
