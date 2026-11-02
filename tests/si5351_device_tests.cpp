// SPDX-License-Identifier: MIT
#include "rf/si5351_device.hpp"

#include <algorithm>
#include <cassert>
#include <vector>

using namespace wsprrypico::rf::si5351;
namespace {
struct MemoryBus : Bus {
    std::array<std::uint8_t, 256> registers{};
    unsigned operations = 0, fail_at = 0, writes = 0;
    std::uint64_t expected_deadline = 100;
    bool corrupt = false;
    std::vector<std::uint8_t> written;
    std::vector<std::array<std::uint8_t, 256>> reset_maps;
    bool read(std::uint8_t reg, std::span<std::uint8_t> bytes, std::uint64_t deadline) override {
        assert(deadline == expected_deadline);
        if (++operations == fail_at)
            return false;
        std::copy_n(registers.begin() + reg, bytes.size(), bytes.begin());
        if (corrupt && reg == 183)
            bytes[0] ^= 1;
        return true;
    }
    bool write(std::uint8_t reg, std::span<const std::uint8_t> bytes,
               std::uint64_t deadline) override {
        assert(deadline == expected_deadline);
        ++writes;
        written.push_back(reg);
        if (++operations == fail_at) {
            registers[reg] = bytes.front(); // Partial mutation before timeout/NACK.
            return false;
        }
        std::copy(bytes.begin(), bytes.end(), registers.begin() + reg);
        if (reg == 177) {
            reset_maps.push_back(registers);
            registers[177] &= 0x5f; // Self-clearing bits.
        }
        return true;
    }
};
} // namespace
int main() {
    Configuration config{25'000'000, Reference::Crystal, 8, Output::Clk1, Output::Clk0, 4};
    const std::uint64_t frequencies[]{14'097'100'000'000'000ULL, 14'097'101'464'843'750ULL};
    const auto result = plan(config, frequencies, 0, 0.001L);
    assert(result.plan);
    MemoryBus bus;
    Device device(bus);
    assert(device.transmit_state() == ClockOutputState::Unknown);
    assert(device.reference_state() == ClockOutputState::Unknown);
    assert(device.configure(config, *result.plan, 100));
    const auto operations = bus.operations;
    assert(bus.registers[3] == 0xff);
    for (unsigned reg = 19; reg <= 23; ++reg)
        assert(bus.registers[reg] & 0x80); // Internal unused drivers also stay down.
    assert(bus.registers[183] == 0x92);
    assert(device.transmit_state() == ClockOutputState::RegisterDisabled);
    assert(device.reference_state() == ClockOutputState::RegisterDisabled);
    assert(!device.transmit_enabled(true, 100)); // No enable before lock observation.
    assert(!device.reference_enabled(true, 100));
    assert(device.locked(100));
    bus.registers[0] = 0x08; // AN619 LOS_XTAL invalidates both PLL outputs.
    assert(!device.locked(100) && !device.reference_locked());
    assert(!device.transmit_enabled(true, 100) && !device.reference_enabled(true, 100));
    bus.registers[0] = 0x10; // Unused Si5351C CLKIN detector is independent.
    assert(device.locked(100) && device.reference_locked());
    bus.registers[0] = 0x40; // PLLB loss must also invalidate reference lock.
    assert(device.locked(100) && !device.reference_locked());
    assert(!device.reference_enabled(true, 100));
    bus.registers[0] = 0;
    assert(device.locked(100) && device.reference_locked());
    assert(device.reference_enabled(true, 100));
    const auto reference_pll = std::span(bus.registers).subspan(34, 8);
    std::array<std::uint8_t, 8> reference_before{};
    std::copy(reference_pll.begin(), reference_pll.end(), reference_before.begin());
    assert(device.transmit_enabled(true, 100));
    assert(device.transmit_tone(result.plan->tones()[1], 100));
    assert((bus.registers[3] & 3) == 0);
    assert(std::equal(reference_before.begin(), reference_before.end(), reference_pll.begin()));
    assert(device.transmit_enabled(false, 100));
    assert(device.reference_state() == ClockOutputState::RegisterEnabled);
    assert(device.quiesce(100));
    assert(device.transmit_state() == ClockOutputState::RegisterDisabled);
    assert(device.reference_state() == ClockOutputState::RegisterDisabled);
    assert(!device.configured());
    // An old loopback must stop when replaced with None, including CLK0.
    config.loopback.reset();
    const auto none = plan(config, frequencies, 0, 0.001L);
    assert(none.plan && device.configure(config, *none.plan, 100));
    assert(bus.registers[3] == 0xff && (bus.registers[16] & 0x80));
    assert(!device.reference_enabled(true, 100));
    config.loopback = Output::Clk0;
    const auto writes = bus.writes;
    config.reference_hz = 27'000'000;
    assert(!device.configure(config, *result.plan, 100)); // Binding checked before writes.
    assert(bus.writes == writes);
    config = result.plan->configuration;
    auto altered = *result.plan;
    altered.tone_storage[0].multisynth.registers[0] ^= 1;
    assert(!device.configure(config, altered, 100));
    assert(bus.writes == writes);
    altered = *result.plan;
    altered.tone_count = 5;
    assert(altered.tones().empty() && !device.configure(config, altered, 100));
    assert(bus.writes == writes);
    for (unsigned failure = 1; failure <= operations; ++failure) {
        MemoryBus broken;
        broken.fail_at = failure;
        Device candidate(broken);
        assert(!candidate.configure(config, *result.plan, 100));
        assert(!candidate.configured());
        assert(candidate.transmit_state() == ClockOutputState::Unknown);
        broken.fail_at = 0;
        assert(candidate.quiesce(100));
        assert(candidate.transmit_state() == ClockOutputState::RegisterDisabled);
    }
    MemoryBus readback;
    readback.corrupt = true;
    Device bad(readback);
    assert(!bad.configure(config, *result.plan, 100));
    assert(!bad.configured() && bad.transmit_state() == ClockOutputState::Unknown);
    // A crystal -> external XA -> crystal replacement must not retain a stale
    // load selection or select the distinct CLKIN path. Reserved fields follow
    // the owning register's rules, rather than one universal zero-fill value.
    MemoryBus changed;
    changed.registers[15] = 0xff;
    changed.registers[149] = 0xff;
    changed.registers[183] = 0x52;
    Device transitions(changed);
    config.reference = Reference::ExternalXa;
    config.crystal_load_pf.reset();
    auto external = plan(config, frequencies, 0, 0.001L);
    assert(external.plan && transitions.configure(config, *external.plan, 100));
    assert(changed.registers[183] == 0xd2);
    assert(changed.registers[15] == 0xf3);
    assert(changed.registers[149] == 0x7f);
    assert(changed.registers[3] == 0xff);
    config.reference = Reference::Crystal;
    config.crystal_load_pf = 6;
    auto crystal = plan(config, frequencies, 0, 0.001L);
    assert(crystal.plan && transitions.configure(config, *crystal.plan, 100));
    assert(changed.registers[183] == 0x52 && changed.registers[3] == 0xff);
    {
        Configuration high_config{25'000'000,   Reference::ExternalXa, {},
                                  Output::Clk0, Output::Clk2,          2};
        const std::uint64_t high_frequencies[]{144'490'500'000'000'000ULL,
                                               144'490'501'464'843'750ULL};
        const auto high = plan(high_config, high_frequencies, 0, 0.001L);
        assert(high.plan);
        MemoryBus high_bus;
        Device high_device(high_bus);
        assert(high_device.configure(high_config, *high.plan, 100));
        assert(high_device.locked(100));
        assert(high_device.reference_enabled(true, 100));
        const auto reference_map = high_bus.registers;
        const std::uint64_t lf_frequencies[]{137'500'000'000'000ULL};
        const auto lf = plan(high_config, lf_frequencies, 0, 0.001L);
        assert(lf.plan);
        for (const auto* replacement : {&*lf.plan, &*high.plan}) {
            high_bus.reset_maps.clear();
            assert(high_device.configure(high_config, *replacement, 100));
            assert(high_bus.reset_maps.size() == 1);
            const auto& reset = high_bus.reset_maps.front();
            const auto& first = replacement->tones().front();
            assert(std::equal(first.multisynth.registers.begin(), first.multisynth.registers.end(),
                              reset.begin() + 42));
            assert(reset[16] == (first.control | 0x80));
            assert((reset[3] & 1) && !(reset[3] & 4)); // TX disabled, loopback still enabled.
            assert((reset[177] & 0xa0) == 0x20);       // Only PLLA is reset.
            assert(std::equal(reference_map.begin() + 34, reference_map.begin() + 42,
                              reset.begin() + 34));
            assert(std::equal(reference_map.begin() + 58, reference_map.begin() + 66,
                              reset.begin() + 58));
            assert(high_device.locked(100) && high_device.reference_locked());
        }
        assert(high_device.transmit_enabled(true, 100));
        const auto before = high_bus.registers;
        high_bus.written.clear();
        assert(high_device.transmit_tone(high.plan->tones()[1], 100));
        assert(high_bus.written == std::vector<std::uint8_t>{26});
        assert(high_device.transmit_state() == ClockOutputState::RegisterEnabled);
        assert(
            std::equal(before.begin() + 34, before.begin() + 42, high_bus.registers.begin() + 34));
        assert(
            std::equal(before.begin() + 58, before.begin() + 66, high_bus.registers.begin() + 58));
        assert(before[177] == high_bus.registers[177]);
        assert(before[3] == high_bus.registers[3] && before[16] == high_bus.registers[16]);
        high_bus.fail_at = high_bus.operations + 1;
        assert(!high_device.transmit_tone(high.plan->tones()[0], 100));
        assert(high_device.transmit_state() == ClockOutputState::Unknown);
        const auto writes = high_bus.writes;
        assert(!high_device.transmit_tone(high.plan->tones()[0], 100));
        assert(high_bus.writes == writes); // No retry using a stale PLL/MS cache.
        assert(high_device.quiesce(100));
        high_bus.written.clear();
        assert(high_device.configure(high_config, *high.plan, 100));
        assert(std::find(high_bus.written.begin(), high_bus.written.end(), 42) !=
               high_bus.written.end());
    }
}
