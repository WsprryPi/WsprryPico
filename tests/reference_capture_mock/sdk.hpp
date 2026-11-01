// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cassert>
#include <cstdint>

// Behavioral SDK fixture: PWM-selected pins drive unless OE is overridden.
// In particular, the real gpio_set_function clears that override. Every GPIO
// operation checks the resulting electrical direction, including handovers.
using uint = unsigned;
inline constexpr unsigned GPIO_FUNC_PWM = 4, GPIO_FUNC_SIO = 5, GPIO_IN = 0;
inline constexpr unsigned GPIO_OVERRIDE_LOW = 2, GPIO_OVERRIDE_NORMAL = 0;
inline constexpr unsigned IO_BANK0_GPIO0_CTRL_FUNCSEL_LSB = 0;
inline constexpr unsigned IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS = 31;
inline constexpr unsigned PWM_CHAN_B = 1, PWM_DIV_B_RISING = 2;
inline constexpr unsigned clk_sys = 0, clk_ref = 1;
struct gpio_mock {
    std::uint32_t ctrl = GPIO_FUNC_SIO;
};
struct io_bank_mock {
    std::array<gpio_mock, 48> io;
};
inline io_bank_mock mock_bank;
inline io_bank_mock* io_bank0_hw = &mock_bank;
namespace capture_mock {
inline std::array<bool, 48> output{}, input_enabled{}, pulls{};
inline std::array<bool, 8> pwm_enabled{}, irq_enabled{};
inline std::array<std::uint16_t, 8> counters{};
inline unsigned system_hz = 138'000'000, reference_hz = 12'000'000;
inline std::uint64_t raw_us = 1000;
inline unsigned transitions = 0;
inline void check() {
    ++transitions;
    for (unsigned gp = 0; gp < 48; ++gp) {
        const auto control = mock_bank.io[gp].ctrl;
        const bool forced_input = ((control >> 12) & 3) == GPIO_OVERRIDE_LOW;
        const bool pwm = (control & IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS) == GPIO_FUNC_PWM;
        assert(forced_input || (!pwm && !output[gp]));
    }
}
} // namespace capture_mock
inline void hw_write_masked(std::uint32_t* address, std::uint32_t value, std::uint32_t mask) {
    *address = (*address & ~mask) | (value & mask);
    capture_mock::check();
}
inline void gpio_init(unsigned gp) {
    capture_mock::output[gp] = false;
    mock_bank.io[gp].ctrl = GPIO_FUNC_SIO;
    capture_mock::check();
}
inline void gpio_set_dir(unsigned gp, unsigned output) {
    capture_mock::output[gp] = output != GPIO_IN;
    capture_mock::check();
}
inline void gpio_set_function(unsigned gp, unsigned function) {
    mock_bank.io[gp].ctrl = function; // All overrides clear, as in SDK 2.3.1.
    capture_mock::check();
}
inline void gpio_set_oeover(unsigned gp, unsigned value) {
    hw_write_masked(&mock_bank.io[gp].ctrl, value << 12, 3u << 12);
}
inline void gpio_disable_pulls(unsigned gp) {
    capture_mock::pulls[gp] = false;
}
inline void gpio_set_input_enabled(unsigned gp, bool value) {
    capture_mock::input_enabled[gp] = value;
}
inline unsigned pwm_gpio_to_slice_num(unsigned gp) {
    return (gp >> 1) & 7;
}
inline unsigned pwm_gpio_to_channel(unsigned gp) {
    return gp & 1;
}
struct pwm_config {
    unsigned mode = 0, divider = 1;
};
inline pwm_config pwm_get_default_config() {
    return {};
}
inline void pwm_config_set_clkdiv_mode(pwm_config* config, unsigned mode) {
    config->mode = mode;
}
inline void pwm_config_set_clkdiv_int(pwm_config* config, unsigned divider) {
    config->divider = divider;
}
inline void pwm_set_enabled(unsigned slice, bool enabled) {
    capture_mock::pwm_enabled[slice] = enabled;
    capture_mock::check();
}
inline void pwm_init(unsigned slice, const pwm_config* config, bool enabled) {
    assert(config->mode == PWM_DIV_B_RISING && config->divider == 1);
    pwm_set_enabled(slice, enabled);
}
inline void pwm_set_irq_enabled(unsigned slice, bool enabled) {
    capture_mock::irq_enabled[slice] = enabled;
}
inline void pwm_clear_irq(unsigned) {}
inline void pwm_set_counter(unsigned slice, std::uint16_t value) {
    capture_mock::counters[slice] = value;
}
inline std::uint16_t pwm_get_counter(unsigned slice) {
    return capture_mock::counters[slice];
}
inline unsigned clock_get_hz(unsigned clock) {
    return clock == clk_sys ? capture_mock::system_hz : capture_mock::reference_hz;
}
inline std::uint64_t time_us_64() {
    return capture_mock::raw_us;
}
