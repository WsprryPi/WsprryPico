#pragma once

#include <array>
#include <cstdint>
#include <span>

namespace wsprrypico::wtp {

using PayloadDigest = std::array<std::uint8_t, 32>;

PayloadDigest sha256(std::span<const std::uint8_t> bytes);

} // namespace wsprrypico::wtp
