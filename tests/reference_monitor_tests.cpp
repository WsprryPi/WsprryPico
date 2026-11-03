// SPDX-License-Identifier: MIT
#include "rf/reference_monitor.hpp"
#include "time/gps_calibration.hpp"

#include <algorithm>
#include <cassert>
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
} // namespace
int main() {
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
