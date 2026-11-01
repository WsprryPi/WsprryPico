// SPDX-License-Identifier: MIT
#include "rf/si5351_plan.hpp"

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
    const std::uint64_t invalid[]{144'490'500'000'000'000ULL};
    assert(!plan(config, invalid, 0, 0.001L).plan);
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
