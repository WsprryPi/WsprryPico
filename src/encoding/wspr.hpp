#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::encoding {
using Symbols = std::array<std::uint8_t, 162>;
// Type 1 only: uppercase ordinary callsign, four-character locator, exact dBm.
// Rejects unsupported messages instead of silently altering station identity.
[[nodiscard]] std::optional<Symbols> wspr_type1(std::string_view call, std::string_view grid,
                                                unsigned dbm);
} // namespace wsprrypico::encoding
