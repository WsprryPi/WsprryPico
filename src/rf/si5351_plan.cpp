// SPDX-License-Identifier: MIT
#include "rf/si5351_plan.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>

namespace wsprrypico::rf::si5351 {
namespace {
constexpr std::uint32_t maximum_denominator = 1'048'575;
bool output_valid(Output value) {
    return value == Output::Clk0 || value == Output::Clk1 || value == Output::Clk2;
}
std::optional<Divider> divider(long double ratio, unsigned r_code = 0) {
    if (!std::isfinite(ratio) || ratio < 8 || ratio > 2048 || r_code > 7)
        return {};
    auto a = static_cast<std::uint32_t>(std::floor(ratio));
    // Bounded continued fractions, including the last legal semiconvergent.
    const auto target = ratio - a;
    long double remainder = target;
    std::uint64_t p0 = 0, q0 = 1, p1 = 1, q1 = 0;
    for (unsigned iteration = 0; iteration < 64; ++iteration) {
        if (!std::isfinite(remainder))
            break;
        const auto floor = std::floor(remainder);
        if (floor > maximum_denominator || (q1 && floor > (maximum_denominator - q0) / q1))
            break;
        const auto coefficient = static_cast<std::uint64_t>(floor);
        const auto p2 = p0 + coefficient * p1, q2 = q0 + coefficient * q1;
        p0 = p1;
        q0 = q1;
        p1 = p2;
        q1 = q2;
        const auto fractional = remainder - floor;
        if (fractional == 0)
            break;
        remainder = 1 / fractional;
    }
    if (!q1)
        return {};
    const auto scale = (maximum_denominator - q0) / q1;
    const auto bp = p0 + scale * p1, bq = q0 + scale * q1;
    if (bq && std::fabs(static_cast<long double>(bp) / bq - target) <
                  std::fabs(static_cast<long double>(p1) / q1 - target)) {
        p1 = bp;
        q1 = bq;
    }
    if (p1 == q1) {
        ++a;
        p1 = 0;
        q1 = 1;
    }
    const auto common = std::gcd(p1, q1);
    const auto b = static_cast<std::uint32_t>(p1 / common);
    const auto c = static_cast<std::uint32_t>(q1 / common);
    const auto d = 128ULL * b / c;
    Divider result;
    result.integer = a;
    result.numerator = b;
    result.denominator = c;
    result.p1 = static_cast<std::uint32_t>(128ULL * a + d - 512);
    result.p2 = static_cast<std::uint32_t>(128ULL * b - c * d);
    result.p3 = c;
    if (result.p1 >= (1u << 18) || result.p2 >= (1u << 20) || c > maximum_denominator)
        return {};
    const auto p = result.p1, q = result.p2;
    result.registers = {static_cast<std::uint8_t>(c >> 8),
                        static_cast<std::uint8_t>(c),
                        static_cast<std::uint8_t>(((p >> 16) & 3) | (r_code << 4)),
                        static_cast<std::uint8_t>(p >> 8),
                        static_cast<std::uint8_t>(p),
                        static_cast<std::uint8_t>(((c >> 16) << 4) | ((q >> 16) & 15)),
                        static_cast<std::uint8_t>(q >> 8),
                        static_cast<std::uint8_t>(q)};
    return result;
}
std::optional<Tone> tone(std::uint64_t requested, long double target, long double pll,
                         unsigned drive, bool pll_b, long double maximum_error) {
    // A fixed PLL avoids symbol-time resets. The 8 minimum intentionally
    // excludes special /4 and /6 plans, which need a separate transition plan.
    if (!requested || !std::isfinite(target) || target <= 0)
        return {};
    unsigned r_code = 0;
    // Keep the MultiSynth output at least 1 MHz before the final R divider,
    // matching the conservative low-frequency strategy of the Pi engine.
    while ((target * (1u << r_code) < 1'000'000 || pll / (target * (1u << r_code)) > 2048) &&
           r_code < 7)
        ++r_code;
    if (target * (1u << r_code) < 1'000'000)
        return {};
    auto ms = divider(pll / (target * (1u << r_code)), r_code);
    if (!ms)
        return {};
    Tone result;
    result.requested_nhz = requested;
    result.programmed_hz = target;
    result.multisynth = *ms;
    result.r_divider = 1u << r_code;
    result.achieved_hz = pll / ms->ratio() / result.r_divider;
    result.error_hz = result.achieved_hz - target;
    if (std::fabs(result.error_hz) > maximum_error)
        return {};
    const bool integer = ms->numerator == 0 && ms->integer % 2 == 0;
    result.control = static_cast<std::uint8_t>(0x0c | (pll_b ? 0x20 : 0) | (integer ? 0x40 : 0) |
                                               (drive / 2 - 1));
    return result;
}
std::optional<Tone> pll_tone(std::uint64_t requested, long double target, std::uint32_t reference,
                             unsigned drive, unsigned integer_ms, long double maximum_error,
                             std::uint32_t low, std::uint32_t high, std::uint32_t common_p1,
                             std::uint32_t& remaining_candidates) {
    if ((integer_ms != 4 && integer_ms != 6) || target <= 0 || target > maximum_output_hz ||
        target * integer_ms < 600'000'000 || target * integer_ms > 900'000'000)
        return {};
    const auto ratio = target * integer_ms / reference;
    if (ratio < 15 || ratio > 90)
        return {};
    const auto integer = static_cast<std::uint32_t>(std::floor(ratio));
    const auto fraction = ratio - integer;
    for (auto c = high; c >= low && remaining_candidates; --c) {
        --remaining_candidates;
        auto b = static_cast<std::uint32_t>(std::round(fraction * c));
        if (std::fabs(fraction * c - b) > maximum_error * integer_ms / reference * c)
            continue;
        auto a = integer;
        if (b == c) {
            ++a;
            b = 0;
        }
        Divider pll;
        pll.integer = a;
        pll.numerator = b;
        pll.denominator = c;
        const auto d = 128ULL * b / c;
        pll.p1 = static_cast<std::uint32_t>(128ULL * a + d - 512);
        pll.p2 = static_cast<std::uint32_t>(128ULL * b - c * d);
        pll.p3 = c;
        if (pll.p1 != common_p1)
            continue;
        const auto p = pll.p1, q = pll.p2;
        pll.registers = {static_cast<std::uint8_t>(c >> 8),
                         static_cast<std::uint8_t>(c),
                         static_cast<std::uint8_t>((p >> 16) & 3),
                         static_cast<std::uint8_t>(p >> 8),
                         static_cast<std::uint8_t>(p),
                         static_cast<std::uint8_t>(((c >> 16) << 4) | ((q >> 16) & 15)),
                         static_cast<std::uint8_t>(q >> 8),
                         static_cast<std::uint8_t>(q)};
        Tone result;
        result.requested_nhz = requested;
        result.programmed_hz = target;
        result.pll = pll;
        result.multisynth.integer = integer_ms;
        result.multisynth.p1 = integer_ms == 6 ? 256 : 0;
        result.multisynth.registers = {0,
                                       1,
                                       static_cast<std::uint8_t>(integer_ms == 4 ? 0x0c : 0),
                                       static_cast<std::uint8_t>(result.multisynth.p1 >> 8),
                                       static_cast<std::uint8_t>(result.multisynth.p1),
                                       0,
                                       0,
                                       0};
        result.control = static_cast<std::uint8_t>(0x4c | (drive / 2 - 1));
        result.achieved_hz = pll.ratio() * reference / integer_ms;
        result.error_hz = result.achieved_hz - target;
        if (std::fabs(result.error_hz) <= maximum_error)
            return result;
    }
    return {};
}
} // namespace
long double Divider::ratio() const {
    return integer + static_cast<long double>(numerator) / denominator;
}
std::string_view validate(const Configuration& config) {
    if (config.reference_hz != 25'000'000 && config.reference_hz != 27'000'000)
        return "unsupported_reference_frequency";
    if (config.reference != Reference::Crystal && config.reference != Reference::ExternalXa)
        return "unsupported_reference_arrangement";
    if (config.reference == Reference::Crystal) {
        if (!config.crystal_load_pf ||
            (*config.crystal_load_pf != 6 && *config.crystal_load_pf != 8 &&
             *config.crystal_load_pf != 10))
            return "invalid_crystal_load";
    } else if (config.crystal_load_pf)
        return "inactive_crystal_load";
    if (!output_valid(config.transmit) || (config.loopback && !output_valid(*config.loopback)))
        return "unsupported_output";
    if (config.loopback && *config.loopback == config.transmit)
        return "output_conflict";
    if (config.drive_ma != 2 && config.drive_ma != 4 && config.drive_ma != 6 &&
        config.drive_ma != 8)
        return "invalid_drive";
    return {};
}
std::optional<std::uint8_t> crystal_load_register(const Configuration& config) {
    if (!validate(config).empty())
        return {};
    const unsigned load = config.reference == Reference::ExternalXa ? 10 : *config.crystal_load_pf;
    const unsigned code = load == 6 ? 1 : load == 8 ? 2 : 3;
    return static_cast<std::uint8_t>(0x12 | (code << 6));
}
std::optional<ReferencePlan> plan_reference(const Configuration& config) {
    if (!validate(config).empty() || !config.loopback)
        return {};
    const auto pll = divider(899'000'000.L / config.reference_hz);
    if (!pll || pll->ratio() < 15 || pll->ratio() > 90)
        return {};
    const auto hz = pll->ratio() * config.reference_hz;
    const auto output = tone(1'000'000'000'000'000ULL, 1'000'000, hz, 2, true, 0.001L);
    if (!output)
        return {};
    return ReferencePlan{config, *pll, *output, hz};
}
bool valid_reference_plan(const ReferencePlan& supplied) {
    const auto rebuilt = plan_reference(supplied.configuration);
    return rebuilt && *rebuilt == supplied;
}
Result plan(const Configuration& config, std::span<const std::uint64_t> frequencies,
            std::int32_t correction, long double maximum_error) {
    if (const auto error = validate(config); !error.empty())
        return {{}, error};
    if (frequencies.empty() || frequencies.size() > Plan::maximum_tones)
        return {{}, "invalid_plan_size"};
    if (correction < -correction_limit_ppb || correction > correction_limit_ppb)
        return {{}, "invalid_correction"};
    if (!std::isfinite(maximum_error) || maximum_error < 0 || maximum_error > 1)
        return {{}, "invalid_quantization_budget"};
    Plan result;
    result.configuration = config;
    result.correction_ppb = correction;
    result.maximum_error_hz = maximum_error;
    // Positive correction means a fast source. Program lower RF exactly once;
    // the loopback plan always describes the uncorrected nominal oscillator.
    const auto factor = 1 + static_cast<long double>(correction) / 1'000'000'000;
    // Leave rounding margin below the 900 MHz VCO ceiling.
    const auto pll = divider(899'000'000.L / config.reference_hz);
    if (!pll || pll->ratio() < 15 || pll->ratio() > 90)
        return {{}, "invalid_pll"};
    result.transmit_pll = *pll;
    result.transmit_pll_hz = pll->ratio() * config.reference_hz;
    long double lowest = maximum_output_hz, highest = 0;
    for (const auto requested : frequencies) {
        const auto target = static_cast<long double>(requested) / 1'000'000'000 / factor;
        if (requested < minimum_output_hz * 1'000'000'000ULL || target > maximum_output_hz)
            return {{}, "unsupported_frequency_or_quantization"};
        lowest = std::min(lowest, target);
        highest = std::max(highest, target);
    }
    unsigned integer_ms = 0;
    if (highest > result.transmit_pll_hz / 8) {
        if (lowest * 6 >= 600'000'000 && highest * 6 <= 900'000'000)
            integer_ms = 6;
        else if (lowest * 4 >= 600'000'000 && highest * 4 <= 900'000'000)
            integer_ms = 4;
        else
            return {{}, "incompatible_pll_tone_set"};
    }
    if (integer_ms) {
        const auto initial_ratio = static_cast<long double>(frequencies.front()) / 1e9L / factor *
                                   integer_ms / config.reference_hz;
        const auto common_p1 = static_cast<std::uint32_t>(std::floor(128 * initial_ratio) - 512);
        for (const auto requested : frequencies) {
            const auto ratio = static_cast<long double>(requested) / 1e9L / factor * integer_ms /
                               config.reference_hz;
            if (static_cast<std::uint32_t>(std::floor(128 * ratio) - 512) != common_p1)
                return {{}, "incompatible_vhf_feedback_integer"};
        }
        // Search at most sixteen bounded denominator bands. All live PLL
        // tones share P1 and a <=4095 P3 span; no unstable rational fallback.
        auto remaining_candidates = vhf_candidate_evaluations_maximum;
        for (auto high = vhf_denominator_maximum;
             high >= vhf_denominator_minimum && remaining_candidates;) {
            const auto low = std::max(vhf_denominator_minimum, high - vhf_denominator_span_maximum);
            result.tone_count = 0;
            for (const auto requested : frequencies) {
                const auto target = static_cast<long double>(requested) / 1e9L / factor;
                const auto value =
                    pll_tone(requested, target, config.reference_hz, config.drive_ma, integer_ms,
                             maximum_error, low, high, common_p1, remaining_candidates);
                if (!value)
                    break;
                result.tone_storage[result.tone_count++] = *value;
            }
            if (result.tone_count == frequencies.size())
                break;
            if (low == vhf_denominator_minimum)
                break;
            high = low - 1;
        }
        if (result.tone_count != frequencies.size())
            return {{}, "unsupported_vhf_tone_family"};
        result.transmit_pll = *result.tones().front().pll;
        result.transmit_pll_hz = result.transmit_pll.ratio() * config.reference_hz;
    } else {
        for (const auto requested : frequencies) {
            const auto target = static_cast<long double>(requested) / 1e9L / factor;
            const auto value = tone(requested, target, result.transmit_pll_hz, config.drive_ma,
                                    false, maximum_error);
            if (!value)
                return {{}, "unsupported_frequency_or_quantization"};
            result.tone_storage[result.tone_count++] = *value;
        }
    }
    if (config.loopback) {
        result.loopback_pll = *pll;
        result.loopback_pll_hz = pll->ratio() * config.reference_hz;
        result.loopback = tone(1'000'000'000'000'000ULL, 1'000'000, result.loopback_pll_hz, 2, true,
                               maximum_error);
        if (!result.loopback)
            return {{}, "invalid_loopback_plan"};
    }
    return {std::move(result), {}};
}
bool valid_plan(const Plan& supplied) {
    if (!supplied.tone_count || supplied.tone_count > Plan::maximum_tones)
        return false;
    std::array<std::uint64_t, Plan::maximum_tones> frequencies{};
    for (unsigned i = 0; i < supplied.tone_count; ++i)
        frequencies[i] = supplied.tone_storage[i].requested_nhz;
    const auto rebuilt =
        plan(supplied.configuration, std::span(frequencies).first(supplied.tone_count),
             supplied.correction_ppb, supplied.maximum_error_hz);
    return rebuilt.plan && *rebuilt.plan == supplied;
}
} // namespace wsprrypico::rf::si5351
