// SPDX-License-Identifier: MIT
#include "rf/si5351_plan.hpp"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <limits>

using namespace wsprrypico::rf::si5351;
namespace {
// Decode the wire representation, independently of the planner's a+b/c data.
long double decode(const Divider& divider) {
    const auto& r = divider.registers;
    const auto p1 = ((r[2] & 3u) << 16) | (r[3] << 8) | r[4];
    const auto p2 = ((r[5] & 15u) << 16) | (r[6] << 8) | r[7];
    const auto p3 = ((r[5] >> 4) << 16) | (r[0] << 8) | r[1];
    assert(p3 && p3 <= 1'048'575);
    return (p1 + 512.L + static_cast<long double>(p2) / p3) / 128;
}
void frequency_plans() {
    Configuration config{25'000'000, Reference::Crystal, 8, Output::Clk0, Output::Clk2, 2};
    const std::uint64_t tones[]{14'097'097'802'734'375ULL, 14'097'099'267'578'125ULL,
                                14'097'100'732'421'875ULL, 14'097'102'197'265'625ULL};
    for (auto reference : {25'000'000u, 27'000'000u}) {
        config.reference_hz = reference;
        for (auto correction : {-100'000, -1, 0, 1, 100'000}) {
            const auto result = plan(config, tones, correction, 0.001L);
            assert(result.plan && result.error.empty());
            const auto& p = *result.plan;
            assert(valid_plan(p));
            const auto pll = decode(p.transmit_pll) * reference;
            assert(pll >= 600'000'000 && pll <= 900'000'000);
            assert(p.tones().size() == 4);
            for (unsigned i = 0; i < 4; ++i) {
                const auto& t = p.tones()[i];
                const auto actual = pll / decode(t.multisynth) / t.r_divider;
                const auto physical = actual * (1 + correction / 1'000'000'000.L);
                const auto requested = tones[i] / 1'000'000'000.L;
                assert(std::fabs(physical - requested) < 0.0011L);
                assert(std::fabs(actual - t.achieved_hz) < 1e-8L);
                assert((t.control & 0x20) == 0); // PLLA, never loopback PLLB.
                assert((t.control & 0x80) == 0);
                assert(t.programmed_hz * t.r_divider >= 1'000'000);
                if (i)
                    assert(t.achieved_hz > p.tones()[i - 1].achieved_hz);
            }
            assert(p.loopback && p.loopback_pll);
            assert(p.loopback->control & 0x20);
            assert(std::fabs(p.loopback->achieved_hz - 1'000'000) < 0.001L);
            const auto baseline = plan(config, tones, 0, 0.001L);
            assert(baseline.plan);
            assert(p.loopback->multisynth.registers ==
                   baseline.plan->loopback->multisynth.registers);
        }
    }
    // Long-wave R-divider plans and HF / VHF boundary behavior.
    for (auto hz : {8'000ULL, 137'500ULL, 475'700ULL, 1'838'100ULL, 50'294'500ULL, 70'400'000ULL,
                    100'000'000ULL}) {
        const std::uint64_t frequencies[]{hz * 1'000'000'000};
        assert(plan(config, frequencies, 0, 0.001L).plan);
    }
    const std::uint64_t invalid[]{160'000'001'000'000'000ULL};
    assert(!plan(config, invalid, 0, 0.001L).plan);
    for (const auto reference : {25'000'000u, 27'000'000u}) {
        config.reference_hz = reference;
        const auto reference_plan = plan_reference(config);
        assert(reference_plan);
        for (const auto base : {144'490'500ULL, 159'000'000ULL}) {
            std::array<std::uint64_t, 4> vhf{};
            for (unsigned i = 0; i < 4; ++i)
                vhf[i] = base * 1'000'000'000 + i * 1'464'843'750ULL;
            const auto high = plan(config, vhf, 0, 0.001L);
            assert(high.plan && valid_plan(*high.plan));
            assert(high.plan->loopback_pll == reference_plan->pll);
            assert(high.plan->loopback->multisynth == reference_plan->output.multisynth);
            auto minimum_c = vhf_denominator_maximum, maximum_c = 0U;
            const auto common_p1 = high.plan->tones().front().pll->p1;
            for (unsigned i = 0; i < 4; ++i) {
                const auto& t = high.plan->tones()[i];
                minimum_c = std::min(minimum_c, t.pll->denominator);
                maximum_c = std::max(maximum_c, t.pll->denominator);
                assert(t.pll->p1 == common_p1);
                assert(t.pll->denominator >= vhf_denominator_minimum);
                assert(t.pll->denominator <= vhf_denominator_maximum);
                assert(t.pll && t.r_divider == 1 && (t.control & 0x40));
                assert(t.pll->denominator > 1'048'575 / 2); // Bounded live denominator changes.

                const auto ms =
                    (t.multisynth.registers[2] & 0x0c) == 0x0c ? 4.L : decode(t.multisynth);
                assert(ms == (base < 150'000'000 ? 6 : 4));
                const auto wire_hz = decode(*t.pll) * reference / ms;
                assert(std::fabs(wire_hz - static_cast<long double>(vhf[i]) / 1e9L) <= 0.001L);
                auto corrupt = *high.plan;
                corrupt.tone_storage[i].pll->registers[0] ^= 1;
                assert(!valid_plan(corrupt));
            }
            assert(maximum_c - minimum_c <= vhf_denominator_span_maximum);
            if (base == 144'490'500ULL) {
                for (auto& frequency : vhf)
                    frequency -= 2'197'265'625ULL;
                const auto centered = plan(config, vhf, 0, 0.001L);
                assert(centered.plan);
                std::reverse(vhf.begin(), vhf.end());
                const auto reversed = plan(config, vhf, 0, 0.001L);
                assert(reversed.plan);
                for (const auto& tone : centered.plan->tones()) {
                    const auto found =
                        std::find_if(reversed.plan->tones().begin(), reversed.plan->tones().end(),
                                     [&](const auto& other) {
                                         return other.requested_nhz == tone.requested_nhz;
                                     });
                    assert(found != reversed.plan->tones().end() && *found == tone);
                    const auto wire = decode(*tone.pll) * reference /
                                      static_cast<long double>(tone.multisynth.integer);
                    assert(std::fabs(wire - static_cast<long double>(tone.requested_nhz) / 1e9L) <=
                           .001L);
                }
            }
        }
    }
    config.reference_hz = 25'000'000;
    const std::uint64_t crossing_p1[]{144'498'697'000'000'000ULL, 144'498'701'000'000'000ULL};
    assert(!plan(config, crossing_p1, 0, 0.001L).plan);
    const std::uint64_t too_low[]{7'000'000'000'000ULL};
    assert(!plan(config, too_low, 0, 0.001L).plan);
    config.loopback.reset();
    const auto none = plan(config, tones, 0, 0.001L);
    assert(none.plan && !none.plan->loopback && !none.plan->loopback_pll);
    config.loopback = Output::Clk0;
    assert(!plan(config, tones, 0, 0.001L).plan);
    config.transmit = Output::Clk1;
    assert(plan(config, tones, 0, 0.001L).plan); // CLK0 is not None.
    assert(!plan(config, {}, 0, 0.001L).plan);
    assert(!plan(config, tones, 100'001, 0.001L).plan);
    assert(!plan(config, tones, 0, std::numeric_limits<long double>::quiet_NaN()).plan);
    assert(!plan(config, tones, 0, -1).plan);
    const std::uint64_t zero[]{0};
    assert(!plan(config, zero, 0, 0.001L).plan);
}
void configuration() {
    Configuration c;
    assert(!validate(c).empty());
    c.reference_hz = 25'000'000;
    assert(!validate(c).empty());
    for (auto [load, value] : {std::pair{6u, 0x52}, {8u, 0x92}, {10u, 0xd2}}) {
        c.crystal_load_pf = load;
        assert(validate(c).empty());
        assert(crystal_load_register(c) == value);
    }
    c.crystal_load_pf = 0;
    assert(!validate(c).empty());
    c.reference = Reference::ExternalXa;
    assert(!validate(c).empty()); // Inactive crystal setting is rejected.
    c.crystal_load_pf.reset();
    assert(validate(c).empty());
    assert(crystal_load_register(c) == 0xd2); // Deterministic external-XA reset setting.
    for (auto drive : {2u, 4u, 6u, 8u}) {
        c.drive_ma = drive;
        assert(validate(c).empty());
    }
    c.drive_ma = 12;
    assert(!validate(c).empty());
    c.drive_ma = 2;
    c.transmit = static_cast<Output>(3);
    assert(!validate(c).empty());
}
} // namespace
int main() {
    configuration();
    frequency_plans();
}
