// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/pins.hpp"

#include <array>
#include <cstdint>

namespace wsprrypico::hardware {
struct FilterOutput {
    unsigned id = 0, gp = 0;
    std::string name;
    bool active_high = true;
    bool operator==(const FilterOutput&) const = default;
};
struct FilterRange {
    std::string name;
    unsigned selector = 0, low_hz = 0, high_hz = 0;
    bool operator==(const FilterRange&) const = default;
};
// Five outputs match a small direct-GPIO bank. Ten mappings allow shared paths
// without allocating a pin twice. All execution walks have fixed bounds.
struct FilterSettings {
    static constexpr unsigned maximum_outputs = 5, maximum_ranges = 10;
    static constexpr unsigned maximum_delay_ms = 250;
    static constexpr std::size_t maximum_bytes = 1536;
    bool required = false;
    unsigned release_ms = 20, settle_ms = 20, output_count = 0, range_count = 0;
    std::array<FilterOutput, maximum_outputs> outputs{};
    std::array<FilterRange, maximum_ranges> ranges{};
    bool operator==(const FilterSettings&) const = default;
    std::uint64_t preparation_ns() const {
        return required ? std::uint64_t(release_ms + settle_ms) * 1'000'000 : 0;
    }
};
std::string validate_filters(const FilterSettings&, const PinPlan&);
std::optional<FilterSettings> parse_filters(std::string_view);
std::string serialize_filters(const FilterSettings&);
std::string filter_capabilities();
} // namespace wsprrypico::hardware
