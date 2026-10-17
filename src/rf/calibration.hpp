#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::rf {
// Positive means a fast source oscillator. Carrier only; never symbol timing.
inline constexpr std::int32_t correction_limit_ppb = 100'000;
std::optional<std::int32_t> parse_ppm(std::string_view text);
std::string format_ppm(std::int32_t ppb);
} // namespace wsprrypico::rf
