#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::encoding {
using Symbols = std::array<std::uint8_t, 162>;
// Station identity is saved in full, independently of Type 1 encodability.
// Callsigns: 3..12 uppercase letters/digits, optional nonempty slash segments,
// with at least one letter and digit. Locators: four or six characters.
[[nodiscard]] bool valid_station_details(std::string_view call, std::string_view locator,
                                         unsigned dbm);
// Type 1 only: uppercase ordinary callsign, four-character locator, exact dBm.
// Rejects unsupported messages instead of silently altering station identity.
[[nodiscard]] std::optional<Symbols> wspr_type1(std::string_view call, std::string_view grid,
                                                unsigned dbm);
// Station settings retain a four- or six-character uppercase Maidenhead
// locator. Type 1 transmission carries its four-character square only.
[[nodiscard]] std::optional<Symbols>
wspr_type1_from_station(std::string_view call, std::string_view locator, unsigned dbm);
} // namespace wsprrypico::encoding
