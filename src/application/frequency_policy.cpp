#include "application/frequency_policy.hpp"

#include <array>

namespace wsprrypico::application {
namespace {
struct Band {
    std::uint64_t lower_hz, upper_hz;
    bool ordinary;
};
// Correlation envelopes adapted from WsprryPi's Band-Lookup catalog (MIT,
// Copyright 2024 Lee Bussy; see LICENSE.md). Allocated in at least one
// jurisdiction; these ranges do not establish an operator's local authority.
// Experimental ranges require explicit consent; measured points do not qualify
// the complete ranges. 4m/2m lack reliable required WSPR support. Higher bands
// are unqualified and outside the current engine's direct-synthesis limits.
constexpr std::array<Band, 19> bands{{
    {130000, 190000, true},        {472000, 479000, true},        {1800000, 2000000, true},
    {3500000, 4000000, true},      {5250000, 5450000, true},      {7000000, 7300000, true},
    {10100000, 10150000, true},    {14000000, 14350000, true},    {18068000, 18168000, true},
    {21000000, 21450000, true},    {24890000, 24990000, true},    {28000000, 29700000, true},
    {40000000, 45000000, false},   {50000000, 54000000, true},    {54000001, 68000000, false},
    {69900000, 70500000, false},   {144000000, 148000000, false}, {219000000, 225000000, false},
    {420000000, 450000000, false},
}};
constexpr std::uint64_t nhz_per_hz = 1'000'000'000;
} // namespace
FrequencyDisposition frequency_disposition(std::uint64_t frequency_nhz) {
    for (const auto& band : bands) {
        if (frequency_nhz >= band.lower_hz * nhz_per_hz &&
            frequency_nhz <= band.upper_hz * nhz_per_hz)
            return band.ordinary ? FrequencyDisposition::OrdinaryAmateur
                                 : FrequencyDisposition::UnqualifiedAmateur;
    }
    return FrequencyDisposition::NonAmateur;
}
bool frequency_allowed(std::uint64_t frequency_nhz, bool allow_unqualified_frequency,
                       bool allow_non_amateur_frequency) {
    if (frequency_nhz == 0)
        return false;
    switch (frequency_disposition(frequency_nhz)) {
    case FrequencyDisposition::OrdinaryAmateur:
        return true;
    case FrequencyDisposition::UnqualifiedAmateur:
        return allow_unqualified_frequency;
    case FrequencyDisposition::NonAmateur:
        return allow_unqualified_frequency && allow_non_amateur_frequency;
    }
    return false;
}
} // namespace wsprrypico::application
