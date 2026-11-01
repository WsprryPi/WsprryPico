// SPDX-License-Identifier: MIT
#include "rf/pico/reference_capture.hpp"

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/structs/io_bank0.h"
#include "pico/time.h"

namespace wsprrypico::rf {
unsigned PicoReferenceCapture::claimed_slices_ = 0;
bool PicoReferenceCapture::open(const hardware::PinPlan& plan,
                                const hardware::Si5351Settings& settings,
                                const hardware::FilterSettings& filters) {
    if (slice_)
        return false;
    const auto allocation = hardware::validate_si5351(plan, settings, claimed_slices_, filters);
    if (!allocation.valid() || !allocation.pwm_slice || !settings.loopback_input)
        return false;
    const auto gp = *settings.loopback_input, slice = *allocation.pwm_slice;
    // Check the actual SDK mapping in addition to portable resource validation.
    if (pwm_gpio_to_slice_num(gp) != slice || pwm_gpio_to_channel(gp) != PWM_CHAN_B)
        return false;
    claimed_slices_ |= 1u << slice;
    slice_ = slice;
    gpio_ = gp;
    pwm_set_enabled(slice, false);
    gpio_init(gp);
    gpio_set_dir(gp, GPIO_IN);
    gpio_set_oeover(gp, GPIO_OVERRIDE_LOW);
    gpio_disable_pulls(gp);
    gpio_set_input_enabled(gp, true);
    // gpio_set_function clears OEOVER and would briefly drive PWM B against
    // the external clock. Change FUNCSEL alone, preserving forced input.
    hw_write_masked(&io_bank0_hw->io[gp].ctrl, GPIO_FUNC_PWM << IO_BANK0_GPIO0_CTRL_FUNCSEL_LSB,
                    IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS);
    auto configuration = pwm_get_default_config();
    pwm_config_set_clkdiv_mode(&configuration, PWM_DIV_B_RISING);
    pwm_config_set_clkdiv_int(&configuration, 1);
    pwm_init(slice, &configuration, false);
    pwm_set_irq_enabled(slice, false); // Extension uses bounded coherent reads.
    pwm_clear_irq(slice);
    system_hz_ = clock_get_hz(clk_sys);
    reference_hz_ = clock_get_hz(clk_ref);
    return true;
}
CounterSample PicoReferenceCapture::snapshot() const {
    const auto before = time_us_64() * 1000ULL;
    const auto value = pwm_get_counter(*slice_);
    // time_us_64 floors its result. Round the upper bracket outward so the
    // peripheral read cannot lie after a falsely exact microsecond endpoint.
    const auto after = (time_us_64() + 1) * 1000ULL;
    return {value, before, after};
}
bool PicoReferenceCapture::begin(std::uint64_t generation) {
    if (!slice_ || running_ || !system_hz_ || !reference_hz_ ||
        clock_get_hz(clk_sys) != system_hz_ || clock_get_hz(clk_ref) != reference_hz_)
        return false;
    pwm_set_counter(*slice_, 0);
    pwm_clear_irq(*slice_);
    pwm_set_enabled(*slice_, true);
    // The PWM counter cannot advance more than once per system-clock cycle.
    // Use that hardware bound plus 1%, not the configured 1 MHz input. Clock
    // tree changes invalidate the run. Starved service fails closed.
    const auto bound = (static_cast<std::uint64_t>(system_hz_) * 101 + 99) / 100;
    previous_ = snapshot();
    generation_ = generation;
    running_ = counter_.begin(previous_, bound, generation);
    if (!running_)
        pwm_set_enabled(*slice_, false);
    return running_;
}
bool PicoReferenceCapture::poll(std::uint64_t generation) {
    if (!slice_ || !running_)
        return false;
    const auto sample = snapshot();
    if (clock_get_hz(clk_sys) != system_hz_ || clock_get_hz(clk_ref) != reference_hz_)
        generation = 0; // Invalidate rather than reinterpreting the old timer model.
    // Core 1 can poll several times within one microsecond. Keep the prior
    // coherent endpoint until the outward-rounded brackets no longer overlap.
    // Do not consume a count here: the next accepted sample includes all edges.
    // An interrupt-widened bracket is likewise discarded, never published.
    // The next accepted endpoint still enforces the original wrap ambiguity
    // bound from the previous accepted endpoint, without relaxing that bound.
    // Clock/generation changes and malformed or backward brackets still reject.
    if (generation == generation_ && sample.before_ns >= previous_.before_ns &&
        sample.after_ns >= sample.before_ns &&
        (sample.before_ns <= previous_.after_ns ||
         sample.after_ns - sample.before_ns > 10'000))
        return true;
    if (!counter_.sample(sample, generation)) {
        pwm_set_enabled(*slice_, false);
        running_ = false;
        return false;
    }
    previous_ = sample;
    return true;
}
ReferenceWindow PicoReferenceCapture::finish() {
    if (!slice_ || !running_)
        return {};
    // Use the last coherent polled endpoint. Do not merge an untimestamped
    // partial count into that window when stopping the peripheral.
    const auto result = counter_.finish();
    pwm_set_enabled(*slice_, false);
    running_ = false;
    return result;
}
void PicoReferenceCapture::close() {
    if (!slice_)
        return;
    pwm_set_enabled(*slice_, false);
    pwm_set_irq_enabled(*slice_, false);
    pwm_clear_irq(*slice_);
    gpio_set_dir(*gpio_, GPIO_IN);
    gpio_set_function(*gpio_, GPIO_FUNC_SIO);
    gpio_set_oeover(*gpio_, GPIO_OVERRIDE_NORMAL);
    claimed_slices_ &= ~(1u << *slice_);
    slice_.reset();
    gpio_.reset();
    running_ = false;
}
} // namespace wsprrypico::rf
