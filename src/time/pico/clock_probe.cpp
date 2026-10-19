// SPDX-License-Identifier: MIT
#include "time/pico/clock_probe.hpp"

#include "hardware/gpio.h"
#include "hardware/structs/iobank0.h"
#include "hardware/structs/padsbank0.h"
#include "hardware/structs/sio.h"
#include "hardware/sync.h"
#include "pico/time.h"

namespace wsprrypico::time {
namespace {
// Core 0 calls synchronously, while RF/schedules are idle and both boot and
// saved pin plans leave this GPIO unallocated. No timer/PIO/DMA claim is used.
class Pin {
  public:
    static constexpr auto gp = ClockProbe::gpio;
    Pin()
        : ctrl_(io_bank0_hw->io[gp].ctrl), pad_(pads_bank0_hw->io[gp]),
          out_((sio_hw->gpio_out >> gp) & 1u), oe_((sio_hw->gpio_oe >> gp) & 1u) {
        const auto function = ctrl_ & IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS;
        valid_ = !oe_ && (ctrl_ == GPIO_FUNC_NULL || ctrl_ == GPIO_FUNC_SIO) &&
                 (function == GPIO_FUNC_NULL || function == GPIO_FUNC_SIO);
        if (valid_) {
            gpio_set_function(gp, GPIO_FUNC_SIO);
            // RP2350-E9: an enabled A2 input can source enough leakage to
            // defeat a weak pull-down. Settle with IE clear; sample briefly.
            gpio_set_input_enabled(gp, false);
            gpio_disable_pulls(gp);
            busy_wait_us_32(200); // Allow a weak external pull and cable capacitance to settle.
        }
    }
    bool valid() const {
        return valid_;
    }
    bool restore() {
        if (!valid_)
            return false;
        // Clear IE separately before isolation can latch its previous state
        // (RP2350-E9), then release output and restore the exact original pad.
        gpio_set_input_enabled(gp, false);
        gpio_set_dir(gp, GPIO_IN);
        gpio_put(gp, out_);
        pads_bank0_hw->io[gp] = pad_;
        io_bank0_hw->io[gp].ctrl = ctrl_;
        valid_ = false;
        return pads_bank0_hw->io[gp] == pad_ && io_bank0_hw->io[gp].ctrl == ctrl_ &&
               ((sio_hw->gpio_oe >> gp) & 1u) == oe_ && ((sio_hw->gpio_out >> gp) & 1u) == out_;
    }
    ~Pin() {
        if (valid_)
            (void)restore();
    }

  private:
    std::uint32_t ctrl_, pad_;
    bool out_, oe_, valid_;
};
bool sample_input(ClockProbeInput* result = nullptr) {
    const auto gp = ClockProbe::gpio;
    const auto interrupts = save_and_disable_interrupts();
    gpio_set_input_enabled(gp, true);
    __dsb();
    busy_wait_us_32(1); // Input synchronizer settling; no long enabled-input hold.
    const bool value = gpio_get(gp);
    if (result) {
        result->pad_sampling = pads_bank0_hw->io[gp];
        result->control_sampling = io_bank0_hw->io[gp].ctrl;
        result->output_enabled = (sio_hw->gpio_oe >> gp) & 1u;
    }
    gpio_set_input_enabled(gp, false);
    restore_interrupts(interrupts);
    return value;
}
} // namespace
std::optional<ClockProbeInput> PicoClockProbe::read() {
    ClockProbeInput result;
    result.pad_before = pads_bank0_hw->io[ClockProbe::gpio];
    Pin pin;
    if (!pin.valid())
        return {};
    // A passive continuity test uses the host's weak pull, not an output.
    // Keep the Pico pulls disabled long enough for the wire/load to settle;
    // leave interrupts enabled and preserve the actual register/read window.
    result.settle_us = 20'000;
    result.pad_settling = pads_bank0_hw->io[ClockProbe::gpio];
    result.raw_before_ns = time_us_64() * 1000ULL;
    busy_wait_us_32(result.settle_us);
    result.level = sample_input(&result);
    result.raw_after_ns = time_us_64() * 1000ULL;
    return pin.restore() ? std::optional(result) : std::nullopt;
}
void PicoClockProbe::pulse(ClockProbeRecord& r) {
    Pin pin;
    if (!pin.valid())
        return;
    const auto gp = ClockProbe::gpio;
    // A high idle input suggests another driver or wrong wiring. Never drive
    // over it. The Pi receiver explicitly requests input with a pull-down.
    if (sample_input()) {
        r.restored = pin.restore();
        return;
    }
    gpio_put(gp, false);
    gpio_set_drive_strength(gp, GPIO_DRIVE_STRENGTH_2MA);
    gpio_set_dir(gp, GPIO_OUT);
    gpio_set_input_enabled(gp, true); // Strong output now controls pad voltage.
    const auto anchor_before = clock_.snapshot();
    const auto interrupts = save_and_disable_interrupts();
    const auto raw_before = time_us_64() * 1000ULL;
    gpio_put(gp, true);
    __dsb();
    busy_wait_us_32(2);
    r.high_readback = gpio_get(gp);
    const auto raw_after = time_us_64() * 1000ULL;
    restore_interrupts(interrupts);
    const auto anchor_after = clock_.snapshot();
    (void)bind_probe_edge(r, anchor_before, anchor_after, raw_before, raw_after);
    // Interrupts remain enabled throughout the 1 ms pulse. Its actual falling
    // edge is recorded, so delayed servicing never masquerades as exact width.
    busy_wait_us_32(ClockProbe::pulse_us);
    r.fall_before_ns = time_us_64() * 1000ULL;
    gpio_put(gp, false);
    __dsb();
    busy_wait_us_32(2);
    r.low_readback = !gpio_get(gp);
    r.fall_after_ns = time_us_64() * 1000ULL;
    r.restored = pin.restore();
}
} // namespace wsprrypico::time
