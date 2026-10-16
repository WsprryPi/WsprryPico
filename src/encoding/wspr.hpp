#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::encoding {
using Symbols = std::array<std::uint8_t, 162>;
inline constexpr std::size_t max_station_token = 12;
enum class WsprType : std::uint8_t { Type1 = 1, Type2 = 2, Type3 = 3 };
struct WsprFrame {
    WsprType type = WsprType::Type1;
    std::uint64_t payload = 0; // Exactly 50 significant bits.
    Symbols symbols{};
};
struct WsprPlan {
    std::array<WsprFrame, 2> frames{};
    unsigned count = 0;
    bool type2_ambiguous = false;
    std::array<char, max_station_token> alternate_call{};
    unsigned alternate_length = 0;
};
// No normalization or substitution. Storage validity is deliberately broader
// than transmission planning. Explicit brackets count toward the token bound.
[[nodiscard]] std::optional<WsprPlan> wspr_plan(std::string_view call, std::string_view locator,
                                                unsigned dbm);
[[nodiscard]] std::uint16_t wspr_hash(std::string_view inner_call);
[[nodiscard]] Symbols wspr_channel(std::uint64_t payload);
// Station identity is saved in full, independently of Type 1 encodability.
// Callsigns: 3..12 uppercase letters/digits, optional nonempty slash segments,
// with at least one letter and digit. Locators: four or six characters.
[[nodiscard]] bool valid_station_details(std::string_view call, std::string_view locator,
                                         unsigned dbm);
[[nodiscard]] bool valid_station_callsign(std::string_view call);
[[nodiscard]] bool valid_station_locator(std::string_view locator);
[[nodiscard]] bool valid_station_power(unsigned dbm);
// Type 1 only: uppercase ordinary callsign, four-character locator, exact dBm.
// Rejects unsupported messages instead of silently altering station identity.
[[nodiscard]] std::optional<Symbols> wspr_type1(std::string_view call, std::string_view grid,
                                                unsigned dbm);
// Station settings retain a four- or six-character uppercase Maidenhead
// locator. Type 1 transmission carries its four-character square only.
[[nodiscard]] std::optional<Symbols>
wspr_type1_from_station(std::string_view call, std::string_view locator, unsigned dbm);
} // namespace wsprrypico::encoding
