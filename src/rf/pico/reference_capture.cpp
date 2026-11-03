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
    unpublish();
    ++capture_id_;
    last_publication_ns_ = 0;
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
    else
        publish();
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
        unpublish();
        pwm_set_enabled(*slice_, false);
        running_ = false;
        return false;
    }
    previous_ = sample;
    publish();
    return true;
}
ReferenceWindow PicoReferenceCapture::finish() {
    if (!slice_ || !running_)
        return {};
    // Use the last coherent polled endpoint. Do not merge an untimestamped
    // partial count into that window when stopping the peripheral.
    const auto result = counter_.finish();
    unpublish();
    pwm_set_enabled(*slice_, false);
    running_ = false;
    return result;
}
void PicoReferenceCapture::close() {
    if (!slice_)
        return;
    unpublish();
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
void PicoReferenceCapture::unpublish() {
    publication_sequence_.fetch_add(1, std::memory_order_acq_rel);
    publication_[0].store(0, std::memory_order_relaxed);
    publication_sequence_.fetch_add(1, std::memory_order_release);
}
void PicoReferenceCapture::publish() {
    const auto window = counter_.finish();
    if (!window.coherent || (last_publication_ns_ &&
        previous_.before_ns >= last_publication_ns_ &&
        previous_.before_ns - last_publication_ns_ < 50'000)) return;
    last_publication_ns_ = previous_.before_ns;
    const std::array<std::uint64_t, 6> values{
        previous_.before_ns, window.edges, generation_, capture_id_, system_hz_, reference_hz_};
    publication_sequence_.fetch_add(1, std::memory_order_acq_rel);
    publication_[0].store(*slice_ + 1, std::memory_order_relaxed);
    publication_[1].store(previous_.counter, std::memory_order_relaxed);
    for (unsigned i = 0; i < values.size(); ++i) {
        publication_[2 + 2 * i].store(std::uint32_t(values[i]), std::memory_order_relaxed);
        publication_[3 + 2 * i].store(std::uint32_t(values[i] >> 32), std::memory_order_relaxed);
    }
    publication_sequence_.fetch_add(1, std::memory_order_release);
}
time::gps::CycleSnapshot PicoReferenceCapture::pps_snapshot() const {
    const auto sequence = publication_sequence_.load(std::memory_order_acquire);
    if (sequence & 1) return {};
    const auto slice = publication_[0].load(std::memory_order_relaxed);
    if (!slice) return {};
    const auto previous_counter = publication_[1].load(std::memory_order_relaxed);
    std::array<std::uint64_t, 6> values{};
    for (unsigned i = 0; i < values.size(); ++i)
        values[i] = publication_[2 + 2 * i].load(std::memory_order_relaxed) |
                    (std::uint64_t(publication_[3 + 2 * i].load(std::memory_order_relaxed)) << 32);
    const auto before = time_us_64() * 1000ULL;
    const auto counter = pwm_get_counter(slice - 1);
    const auto after = (time_us_64() + 1) * 1000ULL;
    // Keep all payload/peripheral reads before the second sequence read on
    // weakly ordered cores; atomic words alone do not make a coherent view.
    std::atomic_thread_fence(std::memory_order_acquire);
    if (publication_sequence_.load(std::memory_order_relaxed) != sequence ||
        after < before || before < values[0] || after - before > 10'000 ||
        after - values[0] > 1'000'000'000ULL || clock_get_hz(clk_sys) != values[4] ||
        clock_get_hz(clk_ref) != values[5]) return {};
    const auto bound = (values[4] * 101 + 99) / 100;
    const auto maximum = ((after - values[0]) * bound + 999'999'999) / 1'000'000'000 + 1;
    const auto delta = std::uint16_t(counter - previous_counter);
    if (maximum >= 65536 || delta > maximum || values[1] > UINT64_MAX - delta) return {};
    return {values[1] + delta, before + (after - before) / 2,
            (after - before + 1) / 2 + 1000, values[2], values[3], true};
}
} // namespace wsprrypico::rf
