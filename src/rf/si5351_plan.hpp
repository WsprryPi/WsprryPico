// SPDX-License-Identifier: MIT
#pragma once

#include "rf/calibration.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace wsprrypico::rf::si5351 {
// AN619 rev. 0.8 register arithmetic, implemented independently. These plans
// describe synthesis, never measured timing, lock, electrical safety or RF.
inline constexpr std::uint64_t minimum_output_hz = 8'000;
inline constexpr std::uint64_t maximum_output_hz = 160'000'000;
inline constexpr std::uint32_t vhf_denominator_minimum = 983'040;
inline constexpr std::uint32_t vhf_denominator_maximum = 1'048'575;
inline constexpr std::uint32_t vhf_denominator_span_maximum = 4095;
inline constexpr std::uint32_t vhf_candidate_evaluations_maximum = 32'768;
enum class Output : std::uint8_t { Clk0, Clk1, Clk2 };
enum class Reference { Crystal, ExternalXa };
struct Configuration {
    bool operator==(const Configuration&) const = default;
    std::uint32_t reference_hz = 0; // No oscillator is inferred from a module name.
    Reference reference = Reference::Crystal;
    std::optional<unsigned> crystal_load_pf;
    Output transmit = Output::Clk0;
    std::optional<Output> loopback; // nullopt is None, never CLK0.
    unsigned drive_ma = 2;
};
struct Divider {
    bool operator==(const Divider&) const = default;
    std::uint32_t integer = 0, numerator = 0, denominator = 1;
    std::uint32_t p1 = 0, p2 = 0, p3 = 1;
    std::array<std::uint8_t, 8> registers{};
    long double ratio() const;
};
struct Tone {
    bool operator==(const Tone&) const = default;
    std::uint64_t requested_nhz = 0;
    long double programmed_hz = 0, achieved_hz = 0, error_hz = 0;
    Divider multisynth;
    std::optional<Divider> pll; // VHF: fixed integer MultiSynth, tone-specific PLLA.
    unsigned r_divider = 1;
    std::uint8_t control = 0;
};
struct ReferencePlan {
    bool operator==(const ReferencePlan&) const = default;
    Configuration configuration;
    Divider pll;
    Tone output;
    long double pll_hz = 0;
};
std::optional<ReferencePlan> plan_reference(const Configuration&);
bool valid_reference_plan(const ReferencePlan&);
struct Plan {
    bool operator==(const Plan&) const = default;
    Configuration configuration;
    Divider transmit_pll; // Initial PLLA; HF keeps it fixed across symbols.
    static constexpr unsigned maximum_tones = 4;
    std::array<Tone, maximum_tones> tone_storage{};
    unsigned tone_count = 0;
    std::span<const Tone> tones() const {
        return tone_count <= maximum_tones ? std::span(tone_storage).first(tone_count)
                                           : std::span<const Tone>{};
    }
    // PLLB and its output are independent of applied transmit correction.
    std::optional<Divider> loopback_pll;
    std::optional<Tone> loopback;
    std::int32_t correction_ppb = 0;
    long double transmit_pll_hz = 0, loopback_pll_hz = 0;
    long double maximum_error_hz = 0;
};
static_assert(sizeof(Plan) <= 2048); // Fixed preparation storage; no heap allocation.
struct Result {
    std::optional<Plan> plan;
    std::string_view error;
};
std::string_view validate(const Configuration&);
// AN619 requires reserved bits 5:0 to be 010010, rather than arbitrary readback.
// External XA restores the documented 10 pF reset setting rather than retaining
// a previous crystal choice. It requires the supported external-XA arrangement;
// this register value alone establishes no electrical suitability.
std::optional<std::uint8_t> crystal_load_register(const Configuration&);
// Stable PLLA / fractional MultiSynth plans only. Frequencies requiring PLL
// retunes are refused; supporting their steady tones would not qualify FSK.
Result plan(const Configuration&, std::span<const std::uint64_t> frequencies_nhz,
            std::int32_t correction_ppb, long double maximum_error_hz);
bool valid_plan(const Plan&);
} // namespace wsprrypico::rf::si5351
