#pragma once

#include <array>
#include <cstdint>
#include <span>

namespace wsprrypico::network {

// Verifies one canonical P-256 SEC1 point and low-S raw ECDSA signature over
// the already constructed 32-byte Owner-HTTP/1 signing digest. No authority is
// granted by this function without challenge/session/journal admission.
bool verify_owner_signature(std::span<const std::uint8_t, 65> public_key,
                            std::span<const std::uint8_t, 32> digest,
                            std::span<const std::uint8_t, 64> signature);

} // namespace wsprrypico::network
