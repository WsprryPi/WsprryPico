// SPDX-License-Identifier: MIT
#include "rf/reference_monitor.hpp"
#include "time/gps_calibration.hpp"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using namespace wsprrypico::rf;
using namespace wsprrypico::rf::si5351;
namespace {
struct BusMemory : Bus {
    std::array<std::uint8_t, 256> registers{};
    std::vector<std::uint8_t> writes;
    bool fail = false;
    bool read(std::uint8_t reg, std::span<std::uint8_t> bytes, std::uint64_t) override {
        if (fail)
            return false;
        std::copy_n(registers.begin() + reg, bytes.size(), bytes.begin());
        return true;
    }
    bool write(std::uint8_t reg, std::span<const std::uint8_t> bytes, std::uint64_t) override {
        writes.push_back(reg);
        std::copy(bytes.begin(), bytes.end(), registers.begin() + reg);
        if (reg == 177)
            registers[reg] &= 0x5f;
        return !fail;
    }
};
struct Capture : ReferenceCapture {
    std::uint64_t& now;
    explicit Capture(std::uint64_t& value) : now(value) {}
    std::uint64_t start = 0, generation = 0;
    unsigned begins = 0, finishes = 0;
    bool missing = false, starved = false;
    bool begin(std::uint64_t g) override {
        start = now;
        generation = g;
        ++begins;
        return true;
    }
    bool poll(std::uint64_t g) override {
        return !starved && g == generation;
    }
    ReferenceWindow finish() override {
        ++finishes;
        return {start, now, missing ? 0 : (now - start) / 1000, 1000, generation, true};
    }
};
std::uint64_t now(void* value) {
    return *static_cast<std::uint64_t*>(value);
}
Configuration configuration() {
    return {25'000'000, Reference::ExternalXa, {}, Output::Clk0, Output::Clk2, 2};
}

void ordinary_calibration_replay() {
    using namespace wsprrypico::time::gps;
    constexpr std::uint64_t second = 1'000'000'000;
    // Production owner/monitor/device and learner, synthetic peripheral only.
    // Poll each modeled millisecond; vary start phase, independent oscillators,
    // post-edge reads and PPS timestamp error. Do not feed a continuous five-
    // minute capture to the learner as if ordinary sessions lasted that long.
    for (const int oscillator : {-20'000, 0, 20'000}) {
        for (const int timer : {-20'000, 20'000}) {
            for (const unsigned phase_ms : {250u, 990u}) {
                BusMemory bus;
                Device device(bus);
                std::uint64_t raw = second;
                Capture capture(raw);
                assert(device.quiesce(raw + 1'000'000));
                ReferenceMonitor monitor(configuration(), ReferencePolicy{}, device, capture, now,
                                         &raw, true);
                PpsCalibration learner;
                unsigned updates = 0;
                int minimum = 100'000, maximum = -100'000;
                std::uint64_t last_generation = 0, paused_stamp = 0;
                std::uint64_t minimum_span = UINT64_MAX, maximum_span = 0;
                for (unsigned ms = phase_ms; ms <= 180'000 + phase_ms; ++ms) {
                    const auto physical = std::uint64_t(ms) * 1'000'000;
                    raw = second + std::uint64_t(std::llround(physical * (1 + timer / 1e9L)));
                    if (ms == 75'250) {
                        assert(monitor.pause(raw + 1'000'000));
                        assert(!monitor.measuring());
                        if (learner.synthesizer())
                            paused_stamp = learner.synthesizer()->observed_raw_ns;
                    }
                    const bool paused = ms >= 75'250 && ms < 77'250;
                    monitor.service(!paused);
                    if (ms % 1000)
                        continue;
                    const auto sequence = ms / 1000;
                    if (sequence == 120 || sequence == 121)
                        continue; // Missing original PPS labels; no replacement.
                    const std::int64_t pps_error = (int(sequence % 7) - 3) * 1000;
                    const auto stamp = std::uint64_t(std::int64_t(raw) + pps_error);
                    const auto delay = sequence % 2 ? 25'000u : 1000u;
                    std::optional<CycleSnapshot> count;
                    if (monitor.measuring() && stamp > capture.start) {
                        const auto start_physical = (capture.start - second) / (1 + timer / 1e9L);
                        const auto read_physical = physical + delay / (1 + timer / 1e9L);
                        const auto frequency = 1'000'000.L * (1 + oscillator / 1e9L);
                        const auto edges =
                            std::uint64_t(std::floor(read_physical * frequency / second)) -
                            std::uint64_t(std::floor(start_physical * frequency / second));
                        count = CycleSnapshot{edges,
                                              raw + delay,
                                              delay + std::uint64_t(std::abs(pps_error)) + 2000,
                                              capture.generation,
                                              capture.begins,
                                              true};
                    }
                    assert(learner.observe(
                        {stamp, 1'800'000'000ULL * second + physical, 200'000, sequence, stamp},
                        count, 1'000'000));
                    if (paused && paused_stamp)
                        assert(learner.synthesizer()->observed_raw_ns == paused_stamp);
                    const auto estimate = learner.synthesizer();
                    if (estimate && estimate->generation != last_generation) {
                        last_generation = estimate->generation;
                        ++updates;
                        // Edge alignment and a slow raw timer can admit twelve
                        // UTC intervals; a sixty-second continuous fit cannot
                        // survive the ordinary session restart.
                        assert(estimate->span_ns >= 10 * second &&
                               estimate->span_ns <= 12 * second);
                        assert(std::abs(estimate->oscillator_error_ppb - oscillator) < 1000);
                        assert(std::uint32_t(std::abs(estimate->oscillator_error_ppb -
                                                      oscillator)) < estimate->uncertainty_ppb);
                        minimum = std::min(minimum, estimate->oscillator_error_ppb);
                        maximum = std::max(maximum, estimate->oscillator_error_ppb);
                        minimum_span = std::min(minimum_span, estimate->span_ns);
                        maximum_span = std::max(maximum_span, estimate->span_ns);
                    }
                }
                assert(capture.begins >= 14 && capture.finishes >= 13 && updates >= 15);
                assert(learner.timer() && learner.timer()->span_ns >= 10 * second);
                const auto final = *learner.synthesizer();
                learner.lost();
                assert(learner.synthesizer()->observed_raw_ns == final.observed_raw_ns);
                assert(!final.fresh(final.observed_raw_ns + 61 * second, 60 * second));
                std::cout << "ordinary-replay source_ppb=" << oscillator << " timer_ppb=" << timer
                          << " phase_ms=" << phase_ms << " sessions=" << capture.begins
                          << " updates=" << updates << " minimum_ppb=" << minimum
                          << " maximum_ppb=" << maximum << " minimum_span_ns=" << minimum_span
                          << " maximum_span_ns=" << maximum_span << '\n';
            }
        }
    }
}
} // namespace
int main() {
    ordinary_calibration_replay();
    BusMemory bus;
    Device device(bus);
    auto config = configuration();
    const auto ref = plan_reference(config);
    assert(ref && valid_reference_plan(*ref));
    auto invalid = *ref;
    invalid.output.multisynth.registers[0] ^= 1;
    assert(!device.configure_reference(config, invalid, 100));
    assert(bus.writes.empty());
    assert(device.configure_reference(config, *ref, 100));
    assert(!device.transmit_configured());
    assert(std::find(bus.writes.begin(), bus.writes.end(), 26) == bus.writes.end());
    assert(std::find(bus.writes.begin(), bus.writes.end(), 42) == bus.writes.end());
    assert(bus.registers[16] == 0x80 && bus.registers[3] == 0xff);
    (void)device.locked(100);
    assert(!device.transmit_enabled(true, 100));
    assert(device.reference_enabled(true, 100));
    const std::uint64_t frequency[]{14'097'100'000'000'000ULL};
    const auto tx = plan(config, frequency, 1000, 0.001L);
    bus.writes.clear();
    assert(tx.plan && device.configure(config, *tx.plan, 100));
    assert(std::find(bus.writes.begin(), bus.writes.end(), 34) == bus.writes.end());
    assert(std::find(bus.writes.begin(), bus.writes.end(), 58) == bus.writes.end());
    assert(device.reference_state() == ClockOutputState::RegisterEnabled);
    assert(device.locked(100) && device.transmit_enabled(true, 100));
    const auto count = bus.writes.size();
    assert(!device.configure(config, *tx.plan, 100) && bus.writes.size() == count);
    assert(device.quiesce(100));
    std::uint64_t raw = 1'000'000;
    Capture capture(raw);
    ReferencePolicy policy;
    ReferenceMonitor monitor(config, policy, device, capture, now, &raw);
    monitor.service(false);
    assert(!monitor.measuring() && !monitor.current());
    monitor.service(true);
    assert(monitor.measuring() && !monitor.current());
    raw += 10'000'000'000ULL;
    monitor.service(true);
    const auto measurement = monitor.current();
    assert(measurement && !measurement->local_rate_ppb);
    assert(device.reference_state() == ClockOutputState::RegisterDisabled);
    assert(device.transmit_state() == ClockOutputState::RegisterDisabled);
    const auto stamp = measurement->observed_raw_ns;
    raw += 1'000'000'000ULL;
    assert(monitor.current()->observed_raw_ns == stamp);
    monitor.service(true);
    assert(monitor.measuring());
    assert(monitor.pause(raw + 1'000'000));
    assert(!monitor.measuring() && monitor.current()->observed_raw_ns == stamp);
    raw += policy.maximum_age_ns;
    assert(!monitor.current());
    monitor.service(true);
    capture.missing = true;
    raw += 10'000'000'000ULL;
    monitor.service(true);
    assert(!monitor.current() && !monitor.measuring());
    assert(monitor.diagnostic() == "missing_signal");
    raw += 1'000'000'000ULL;
    capture.missing = false;
    monitor.service(true);
    assert(monitor.measuring());
    capture.starved = true;
    monitor.service(true);
    assert(!monitor.current() && !monitor.measuring());
    assert(device.reference_state() == ClockOutputState::RegisterDisabled);
    raw += 1'000'000'000ULL;
    capture.starved = false;
    monitor.service(true);
    bus.fail = true;
    assert(!monitor.pause(raw + 1'000'000));
    assert(!monitor.current() && device.reference_state() == ClockOutputState::Unknown);
    bus.fail = false;
    assert(monitor.pause(raw + 1'000'000));
    monitor.inhibit();
    const auto starts = capture.begins;
    monitor.service(true);
    assert(!monitor.current() && capture.begins == starts);
    config.loopback.reset();
    assert(!plan_reference(config));
    // A normal window begins between whole PPS edges. Qualified GPS must retain
    // the same counter session through eleven endpoints for a ten-second fit.
    {
        BusMemory gps_bus;
        Device gps_device(gps_bus);
        std::uint64_t gps_raw = 250'000'000;
        Capture gps_capture(gps_raw);
        assert(gps_device.quiesce(gps_raw + 1'000'000));
        ReferenceMonitor gps_monitor(configuration(), ReferencePolicy{}, gps_device, gps_capture,
                                     now, &gps_raw, true);
        wsprrypico::time::gps::PpsCalibration calibration;
        gps_monitor.service(true);
        assert(gps_monitor.measuring());
        for (unsigned i = 1; i <= 11; ++i) {
            gps_raw = std::uint64_t(i) * 1'000'000'000;
            gps_monitor.service(true);
            assert(gps_monitor.measuring() && gps_capture.begins == 1 && gps_capture.finishes == 0);
            const wsprrypico::time::gps::Observation observation{
                gps_raw, 1'800'000'000'000'000'000ULL + gps_raw, 1000, i, gps_raw};
            const wsprrypico::time::gps::CycleSnapshot cycles{(gps_raw - gps_capture.start) / 1000,
                                                              gps_raw,
                                                              1000,
                                                              gps_capture.generation,
                                                              gps_capture.begins,
                                                              true};
            assert(calibration.observe(observation, cycles, 1'000'000));
        }
        assert(calibration.timer() && calibration.synthesizer());
        assert(calibration.synthesizer()->span_ns == 10'000'000'000ULL);
        // A prepared job still shuts down the reference/counter immediately.
        assert(gps_monitor.pause(gps_raw + 1'000'000));
        assert(!gps_monitor.measuring() && gps_capture.finishes == 1);
        assert(gps_device.reference_state() == ClockOutputState::RegisterDisabled);
    }
}
