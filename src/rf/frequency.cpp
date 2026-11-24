// SPDX-License-Identifier: MIT
#include "rf/waveform.hpp"

namespace wsprrypico::rf {
std::optional<std::uint32_t> frequency_increment(std::uint64_t frequency_nhz,
                                                 std::int32_t correction_ppb) {
    if (frequency_nhz < minimum_frequency_nhz || frequency_nhz > maximum_frequency_nhz ||
        correction_ppb < -max_correction_ppb || correction_ppb > max_correction_ppb)
        return std::nullopt;
    // Exact rounded (frequency_nhz * 2^32) / corrected_sample_rate_nhz.
    // Binary long division avoids 128-bit arithmetic on the Arm target.
    const auto divisor = sample_rate * static_cast<std::uint64_t>(1'000'000'000LL + correction_ppb);
    auto remainder = frequency_nhz;
    std::uint64_t quotient = 0;
    for (unsigned bit = 0; bit < 32; ++bit) {
        remainder *= 2;
        quotient <<= 1;
        if (remainder >= divisor) {
            remainder -= divisor;
            ++quotient;
        }
    }
    if (remainder * 2 >= divisor)
        ++quotient;
    if (quotient == 0 || quotient >= (1ULL << 31))
        return std::nullopt;
    return static_cast<std::uint32_t>(quotient);
}

} // namespace wsprrypico::rf
