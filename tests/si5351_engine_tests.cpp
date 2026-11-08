// SPDX-License-Identifier: MIT
#include "rf/si5351_engine.hpp"

#include <algorithm>
#include <bit>
#include <cassert>
#include <cmath>
#include <iostream>
#include <utility>

#if !defined(__APPLE__)
namespace {
// Model the pinned Arm libm's observed llround/llroundl carry loss above 2^53.
// The target ELF was independently exercised in an instruction emulator. A
// host's correct libm otherwise hides this defect in LOAD/policy projections.
long long target_llround(long double value) {
    const auto magnitude = std::fabs(value);
    assert(std::isfinite(value) && magnitude < 0x1p63L);
    if (magnitude < 0x1p53L)
        return static_cast<long long>(std::round(value));
    const auto bits = std::bit_cast<std::uint64_t>(static_cast<double>(magnitude));
    const auto shift = unsigned((bits >> 52) & 0x7ff) - 1023 - 52;
    const auto high = std::uint64_t((bits >> 32) & 0xfffff) | 0x100000;
    const auto low = std::uint32_t(bits);
    const auto result = (high << (32 + shift)) | std::uint32_t(low << shift);
    return value < 0 ? -static_cast<long long>(result) : static_cast<long long>(result);
}
} // namespace
extern "C" long long llroundl(long double value) noexcept {
    return target_llround(value);
}
extern "C" long long llround(double value) noexcept {
    return target_llround(value);
}
#endif

using namespace wsprrypico;
using namespace wsprrypico::rf::si5351;
namespace {
struct Platform : ExecutionPlatform {
    std::uint64_t now = 1'000'000, cutoff = 0;
    bool gate = false, gate_unknown = false, open = true, pause = true;
    unsigned services = 0;
    std::uint64_t now_ns() const override {
        return now;
    }
    bool initialize() override {
        return open;
    }
    bool set_gate(bool value) override {
        gate = value;
        return !gate_unknown;
    }
    bool gate_active_or_unknown() const override {
        return gate || gate_unknown;
    }
    bool arm_cutoff(std::uint64_t end) override {
        cutoff = end;
        return true;
    }
    void cancel_cutoff() override {
        cutoff = 0;
    }
    bool pause_reference(std::uint64_t) override {
        return pause;
    }
    void service_reference(bool permitted) override {
        if (permitted)
            ++services;
    }
    void inhibit_reference() override {}
};
struct TimedBus : Bus {
    Platform& platform;
    explicit TimedBus(Platform& p) : platform(p) {}
    std::array<std::uint8_t, 256> registers{};
    unsigned writes = 0, operations = 0, fail_at = 0;
    bool unavailable = false, corrupt_mask = false;
    std::uint64_t extra_write_delay = 0;
    bool advance(std::uint64_t duration, std::uint64_t deadline) {
        ++operations;
        platform.now += duration;
        return !unavailable && operations != fail_at && platform.now <= deadline;
    }
    bool read(std::uint8_t reg, std::span<std::uint8_t> bytes, std::uint64_t deadline) override {
        if (!advance((bytes.size() + 3) * 90'000, deadline))
            return false;
        std::copy_n(registers.begin() + reg, bytes.size(), bytes.begin());
        if (corrupt_mask && reg == 3)
            bytes[0] ^= 1;
        return true;
    }
    bool write(std::uint8_t reg, std::span<const std::uint8_t> bytes,
               std::uint64_t deadline) override {
        ++writes;
        // A failed transaction can have changed hardware: never assume NACK
        // or timeout implies that no byte reached a separately powered chip.
        std::copy(bytes.begin(), bytes.end(), registers.begin() + reg);
        if (reg == 177)
            registers[177] &= 0x5f;
        return advance((bytes.size() + 2) * 90'000 + std::exchange(extra_write_delay, 0), deadline);
    }
};
Configuration configuration() {
    return {25'000'000, Reference::ExternalXa, {}, Output::Clk0, Output::Clk2, 2};
}
wtp::Job job(bool keyed = false) {
    wtp::Job result;
    result.job_id = std::string(32, 'a');
    result.mode = keyed ? "qrss" : "fskcw";
    result.allow_frequency_adjustment = true;
    assert(result.events.push_back({0, 100'000'000, true, 14'097'100'000'000'000ULL}));
    assert(result.events.push_back(
        {100'000'000, 100'000'000, !keyed,
         keyed ? std::nullopt : std::optional<std::uint64_t>(14'097'105'000'000'000ULL)}));
    assert(result.events.push_back({200'000'000, 100'000'000, true, 14'097'105'000'000'000ULL}));
    assert(result.events.push_back({300'000'000, 1, false, {}}));
    result.total_duration_ns = 300'000'001;
    return result;
}
struct Clock : wtp::Clock {
    Platform& platform;
    explicit Clock(Platform& value) : platform(value) {}
    bool valid = true;
    std::uint64_t uncertainty = 1000, read_delay = 0;
    wtp::ClockSnapshot snapshot() const override {
        platform.now += read_delay;
        wtp::ClockSnapshot value;
        value.monotonic_now_ns = platform.now;
        value.utc_now_ns = 1'000'000'000'000ULL + platform.now;
        value.uncertainty_ns = uncertainty;
        value.state = valid ? wtp::ClockState::Synchronized : wtp::ClockState::Unsynchronized;
        value.leap = wtp::LeapState::Normal;
        return value;
    }
};
struct Identity : wtp::IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'd');
    }
};
wtp::Request request(std::string op, wtp::RequestBody body, char digit) {
    const auto text = std::string(1, digit);
    return {"WTP/1",
            std::string(32, '1'),
            std::string(32, digit),
            "local",
            std::move(op),
            wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size())),
            std::move(body)};
}
struct Enable : rf::EnableOutput {
    Platform& platform;
    explicit Enable(Platform& value) : platform(value) {}
    bool active = false;
    std::uint64_t on = 0, off = 0;
    bool initialize_inactive() override {
        active = false;
        return true;
    }
    bool write(bool value) override {
        platform.now += 1000;
        active = value;
        (value ? on : off) = platform.now;
        return true;
    }
    bool verify_active() const override {
        return active;
    }
};
struct Fixture {
    Platform platform;
    TimedBus bus{platform};
    Device device{bus};
    Engine engine{configuration(), device, platform, true};
    Fixture() {
        assert(engine.disable(platform.now + 10'000'000));
    }
    std::uint64_t start(wtp::Job value = job()) {
        assert(engine.prepare(value).accepted);
        const auto start = platform.now + 10'000'000;
        assert(engine.begin(value, start));
        platform.now = start;
        assert(engine.poll(start).state == wtp::EngineState::Running);
        const auto observed = engine.observation().enable_command_completed_ns;
        assert(observed == start + 270'000);
        return observed;
    }
};
void replace_complete_transmit_plan() {
    Fixture f;
    std::optional<std::array<std::uint8_t, 256>> reference;
    for (const auto frequency : {144'490'500'000'000'000ULL, 137'500'000'000'000ULL,
                                 144'490'501'464'843'750ULL, 1'838'100'000'000'000ULL}) {
        auto value = job();
        for (auto& event : value.events)
            if (event.rf_on)
                event.frequency_nhz = frequency;
        const std::uint64_t frequencies[]{frequency};
        const auto expected = plan(configuration(), frequencies, 0, 0.001L);
        assert(expected.plan && f.engine.prepare(value).accepted);
        assert(std::equal(expected.plan->transmit_pll.registers.begin(),
                          expected.plan->transmit_pll.registers.end(),
                          f.bus.registers.begin() + 26));
        const auto& tone = expected.plan->tones().front();
        assert(std::equal(tone.multisynth.registers.begin(), tone.multisynth.registers.end(),
                          f.bus.registers.begin() + 42));
        if (!reference) {
            assert(f.device.reference_enabled(true, f.platform.now + 10'000'000));
            reference = f.bus.registers;
        } else {
            assert(std::equal(reference->begin() + 34, reference->begin() + 42,
                              f.bus.registers.begin() + 34));
            assert(std::equal(reference->begin() + 58, reference->begin() + 66,
                              f.bus.registers.begin() + 58));
            assert(f.device.reference_state() == ClockOutputState::RegisterEnabled);
        }
        assert(f.engine.disable(f.platform.now + 10'000'000));
        assert(f.device.transmit_state() == ClockOutputState::RegisterDisabled);
        // Model the idle reference owner's resumption after cleanup.
        assert(f.device.reference_enabled(true, f.platform.now + 10'000'000));
    }
}
void reported_register_frequency() {
    const auto ratio = [](const auto& registers, unsigned offset) {
        const auto p1 = ((registers[offset + 2] & 3u) << 16) |
                        (registers[offset + 3] << 8) | registers[offset + 4];
        const auto p2 = ((registers[offset + 5] & 15u) << 16) |
                        (registers[offset + 6] << 8) | registers[offset + 7];
        const auto p3 = ((registers[offset + 5] >> 4) << 16) |
                        (registers[offset] << 8) | registers[offset + 1];
        assert(p3);
        return (p1 + 512.L + static_cast<long double>(p2) / p3) / 128;
    };
    for (const auto hz : {1'840'100ULL, 5'366'200ULL, 28'126'100ULL, 70'400'000ULL}) {
        for (const auto correction : {-185, -121, 0, 121, 185}) {
            Fixture f;
            auto value = job();
            for (auto& event : value.events)
                if (event.rf_on)
                    event.frequency_nhz = hz * 1'000'000'000;
            assert(f.engine.set_frequency_correction_ppb(correction));
            const auto result = f.engine.prepare(value);
            assert(result.accepted);
            // Decode what the production Device actually wrote, independently
            // of the planner's cached achieved_hz and nHz conversion.
            const auto& registers = f.bus.registers;
            const auto r = 1u << ((registers[44] >> 4) & 7u);
            const auto frequency = ratio(registers, 26) * 25'000'000 /
                                   ratio(registers, 42) / r;
            auto reported = *value.events[0].frequency_nhz;
            for (const auto& adjustment : result.adjustments)
                if (adjustment.event_index == 0)
                    reported = adjustment.realized_frequency_nhz;
            assert(std::fabs(reported / 1'000'000'000.L - frequency) < 0.000001L);
            assert(std::fabs(frequency * (1 + correction / 1e9L) - hz) < 0.0011L);
        }
    }
}
void finite_execution(bool keyed) {
    Fixture f;
    const auto start = f.start(job(keyed));
    assert(f.device.transmit_state() == ClockOutputState::RegisterEnabled);
    const auto reference = std::span(f.bus.registers).subspan(34, 8);
    std::array<std::uint8_t, 8> before{};
    std::copy(reference.begin(), reference.end(), before.begin());
    f.platform.now = start + 100'000'000;
    assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Running);
    assert(f.device.transmit_state() ==
           (keyed ? ClockOutputState::RegisterDisabled : ClockOutputState::RegisterEnabled));
    f.platform.now = start + 200'000'000;
    assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Running);
    assert(f.device.transmit_state() == ClockOutputState::RegisterEnabled);
    assert(std::equal(before.begin(), before.end(), reference.begin()));
    f.platform.now = start + 300'001'000;
    const auto report = f.engine.poll(f.platform.now);
    assert(report.state == wtp::EngineState::Complete);
    assert(f.engine.output_active()); // ACK is deliberately unconfirmed.
    assert(f.engine.observation().disable_command_completed_ns <= start + 308'001'000);
    assert(f.engine.disable(f.platform.now + 10'000'000));
    assert(!f.engine.output_active());
    assert(f.device.reference_state() == ClockOutputState::RegisterDisabled);
}
} // namespace
int main() {
    reported_register_frequency();
    replace_complete_transmit_plan();
    {
        Fixture f;
        auto incompatible = job();
        incompatible.events[0].frequency_nhz = 144'498'697'000'000'000ULL;
        incompatible.events[1].frequency_nhz = 144'498'701'000'000'000ULL;
        incompatible.events[2].frequency_nhz = 144'498'697'000'000'000ULL;
        const auto before = f.bus.writes;
        assert(!f.engine.prepare(incompatible).accepted);
        assert(f.bus.writes == before && !f.engine.output_active());
    }
    for (const bool qualified : {false, true}) {
        Platform platform;
        TimedBus bus(platform);
        Device device(bus);
        Engine engine(configuration(), device, platform, false, nullptr, nullptr, nullptr,
                      qualified);
        assert(engine.disable(platform.now + 10'000'000));
        assert(engine.prepare(job()).accepted == qualified);
        assert(!engine.observation().engineering_allowed);
    }
    {
        Fixture f;
        auto high = job();
        for (auto& event : high.events)
            if (event.frequency_nhz)
                *event.frequency_nhz += 130'393'400'000'000'000ULL;
        const auto start = f.start(high);
        const auto reference = f.bus.registers;
        f.platform.now = start + 100'000'000;
        assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Running);
        assert(std::equal(reference.begin() + 34, reference.begin() + 42,
                          f.bus.registers.begin() + 34));
        f.platform.now = start + 300'001'000;
        assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Complete);
        assert(f.engine.disable(f.platform.now + 10'000'000));
        assert(!f.engine.output_active());
    }
    finite_execution(false);
    finite_execution(true);
    {
        Fixture f;
        f.engine.poll(f.platform.now);
        const auto services = f.platform.services;
        const auto writes = f.bus.writes;
        assert(services > 0);
        assert(f.engine.suspend_background(f.platform.now + 10'000'000));
        assert(!f.engine.suspend_background(f.platform.now + 10'000'000));
        f.platform.now += 20'000'000'000ULL; // Real timer continues through flash lockout.
        f.engine.poll(f.platform.now);
        assert(f.platform.services == services && f.bus.writes == writes);
        assert(!f.engine.prepare(job()).accepted && f.bus.writes == writes);
        f.engine.resume_background();
        f.engine.poll(f.platform.now);
        assert(f.platform.services == services + 1);
        assert(f.engine.suspend_background(f.platform.now + 10'000'000));
        f.engine.inhibit_output();
        f.engine.resume_background();
        f.engine.poll(f.platform.now);
        assert(f.platform.services == services + 1); // Flash exit cannot undo permanent inhibit.
    }
    {
        Fixture f;
        const auto value = job();
        assert(f.engine.prepare(value).accepted);
        const auto services = f.platform.services;
        f.engine.poll(f.platform.now);
        f.platform.now += 120'000'000'000ULL; // A loaded job can wait a full WSPR slot.
        f.engine.poll(f.platform.now);
        assert(f.platform.services == services); // LOAD keeps capture paused before ARM.
        assert(f.engine.suspend_background(f.platform.now + 10'000'000));
        const auto start = f.platform.now + 100'000'000;
        assert(!f.engine.begin(value, start));
        f.engine.resume_background();
        assert(f.engine.begin(value, start)); // The prepared immutable plan survives a pause.
        assert(!f.engine.suspend_background(f.platform.now + 10'000'000)); // Armed.
        f.platform.now = start;
        assert(f.engine.poll(start).state == wtp::EngineState::Running);
        assert(!f.engine.suspend_background(f.platform.now + 10'000'000)); // Running.
        assert(f.engine.disable(f.platform.now + 10'000'000));
        f.engine.poll(f.platform.now);
        assert(f.platform.services == services + 1); // Cleanup releases capture authority.
    }
    {
        Fixture f;
        f.platform.pause = false;
        assert(!f.engine.suspend_background(f.platform.now + 10'000'000));
        assert(f.engine.background_work_allowed());
    }
    {
        Fixture f;
        auto malformed = job();
        malformed.events[1].offset_ns++;
        const auto writes = f.bus.writes;
        assert(!f.engine.prepare(malformed).accepted && f.bus.writes == writes);
        assert(f.engine.set_frequency_correction_ppb(1000));
        assert(f.engine.prepare(job()).accepted);
        assert(!f.engine.set_frequency_correction_ppb(2000));
        auto changed = job();
        changed.events[0].frequency_nhz = 7'040'000'000'000'000ULL;
        assert(!f.engine.begin(changed, f.platform.now + 10'000'000));
    }
    {
        Platform p;
        TimedBus bus(p);
        Device device(bus);
        Engine unqualified(configuration(), device, p, false);
        assert(!unqualified.prepare(job()).accepted && bus.writes == 0);
    }
    {
        Fixture f;
        const auto start = f.start();
        f.platform.now = start + 109'000'000;
        assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Failed);
        assert(!f.engine.output_active());
    }
    {
        Fixture f;
        const auto start = f.start();
        f.bus.extra_write_delay = 9'000'000;
        f.platform.now = start + 300'001'000;
        assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Failed);
        assert(!f.engine.output_active()); // Best-effort verified fault cleanup.
    }
    {
        Fixture f;
        f.start();
        f.bus.unavailable = true;
        assert(!f.engine.disable(f.platform.now + 10'000'000));
        assert(f.engine.output_active());
        assert(f.device.transmit_state() == ClockOutputState::Unknown);
        f.bus.unavailable = false;
        assert(f.engine.disable(f.platform.now + 10'000'000));
        assert(!f.engine.output_active());
    }
    {
        Fixture f;
        f.start();
        f.bus.corrupt_mask = true;
        assert(!f.engine.disable(f.platform.now + 10'000'000));
        assert(f.engine.output_active());
    }
    {
        Fixture f;
        Clock clock(f.platform);
        Identity identity;
        wtp::JobService service(clock, f.engine, identity);
        assert(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        assert(
            service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 10'000}, 'b')).ok);
        auto value = job(true);
        assert(service.handle(request("LOAD", value, 'c')).ok);
        const auto start = f.platform.now + 200'000'000;
        assert(service
                   .handle(request(
                       "ARM", wtp::ArmBody{value.job_id, 1'000'000'000'000ULL + start, 1'000'000},
                       'd'))
                   .ok);
        f.platform.now = start;
        service.poll();
        assert(service.activity().state == wtp::State::Running);
        const auto launched = f.engine.observation().enable_command_completed_ns;
        f.platform.now = launched + 100'000'000;
        service.poll();
        f.platform.now = launched + 200'000'000;
        service.poll();
        f.platform.now = launched + 300'001'000;
        service.poll();
        assert(service.activity().state == wtp::State::Complete);
        assert(!service.activity().output_active);
        assert(service.local_inhibit_output());
        const auto services = f.platform.services;
        (void)f.engine.poll(f.platform.now);
        assert(f.platform.services == services);
        assert(!f.engine.prepare(job()).accepted);
    }
    {
        Platform p;
        TimedBus bus(p);
        Device device(bus);
        Enable output(p);
        rf::AmplifierEnable amplifier(&output, {20, 30});
        assert(amplifier.initialize());
        Engine engine(configuration(), device, p, true, nullptr, &amplifier);
        Clock clock(p);
        assert(engine.disable(p.now + 10'000'000));
        const auto value = job();
        assert(engine.prepare(value).accepted);
        const auto start = p.now + 100'000'000;
        wtp::LocalStartConditions conditions{&clock, 1'000'000'000'000ULL + start, 1'000'000};
        assert(engine.schedule(value, start, conditions));
        p.now = start - 21'000'000;
        assert(engine.poll(p.now).state == wtp::EngineState::Armed);
        assert(output.active);
        p.now = start;
        assert(engine.poll(p.now).state == wtp::EngineState::Running);
        const auto launched = engine.observation().enable_command_completed_ns;
        assert(launched - output.on >= 20'000'000);
        p.now = launched + 100'000'000;
        engine.poll(p.now);
        p.now = launched + 200'000'000;
        engine.poll(p.now);
        p.now = launched + 300'001'000;
        auto report = engine.poll(p.now);
        assert(report.state == wtp::EngineState::Running &&
               report.chain_phase == wtp::ChainPhase::Tail);
        assert(report.tail_deadline_monotonic_ns && output.active);
        assert(device.transmit_state() == ClockOutputState::RegisterDisabled);
        p.now = *report.tail_deadline_monotonic_ns;
        assert(engine.poll(p.now).state == wtp::EngineState::Complete);
        assert(!output.active);
        assert(engine.disable(p.now + 10'000'000));
        assert(engine.observation().amplifier.normal_rf_completion);
    }
    {
        Fixture f;
        Clock clock(f.platform);
        assert(f.engine.prepare(job()).accepted);
        const auto start = f.platform.now + 100'000'000;
        assert(f.engine.schedule(job(), start, {&clock, 1'000'000'000'000ULL + start, 1'000'000}));
        clock.valid = false;
        f.platform.now = start;
        assert(f.engine.poll(f.platform.now).state == wtp::EngineState::Missed);
        assert(!f.engine.output_active());
    }
    {
        Fixture f;
        Clock clock(f.platform);
        assert(f.engine.prepare(job()).accepted);
        const auto start = f.platform.now + 100'000'000;
        assert(f.engine.schedule(job(), start, {&clock, 1'000'000'000'000ULL + start, 1'000'000}));
        // The clock read itself takes time. Comparing its projected deadline
        // with an earlier platform sample otherwise chases a future target.
        clock.read_delay = 1000;
        f.platform.now = start;
        const auto report = f.engine.poll(f.platform.now);
        assert(report.state == wtp::EngineState::Running);
        assert(report.launch_monotonic_ns && *report.launch_monotonic_ns >= start);
        assert(f.engine.disable(f.platform.now + 10'000'000));
    }
    std::cout << "Si5351 finite execution and bounded failure paths passed\n";
}
